"""Reuse either the backend's local runtime or a configured existing Python environment."""
import atexit
import json
import os
from functools import lru_cache
from pathlib import Path
from queue import Queue, Empty
import subprocess
import threading


class LocalEmbedder:
    def __init__(self, path, device, python):
        if not Path(path).is_dir():
            raise ValueError('RAG local model directory does not exist')
        self.path, self.device, self.python = path, device, python
        self.model = None
        self.process = None
        self.lock = threading.Lock()
        self.responses = Queue()
        atexit.register(self.close)

    def close(self):
        if self.process is not None:
            process, self.process = self.process, None
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            for stream in [process.stdin, process.stdout]:
                if stream:
                    stream.close()

    def _read(self, process, queue):
        try:
            for line in process.stdout:
                queue.put(json.loads(line))
        except (ValueError, OSError):
            pass
        finally:
            queue.put({'error': 'Local worker stopped'})

    def _encode(self, texts):
        with self.lock:
            if not self.python:
                if self.model is None:
                    from sentence_transformers import SentenceTransformer
                    self.model = SentenceTransformer(self.path, device=self.device, local_files_only=True)
                return self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False, batch_size=16).tolist()
            if self.process is None or self.process.poll() is not None:
                self.close()
                self.responses = Queue()
                env = {**os.environ, 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
                       'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1'}
                self.process = subprocess.Popen([self.python, str(Path(__file__).with_name('embedding_worker.py')),
                    self.path, self.device], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL, text=True, encoding='utf-8', env=env,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                threading.Thread(target=self._read, args=(self.process, self.responses), daemon=True).start()
            try:
                self.process.stdin.write(json.dumps({'texts': texts}, ensure_ascii=False) + '\n')
                self.process.stdin.flush()
                response = self.responses.get(timeout=120)
                if 'error' in response:
                    raise RuntimeError(response['error'])
                return response['vectors']
            except (Empty, OSError, RuntimeError, KeyError):
                self.close()
                raise RuntimeError('Local embedding worker failed') from None

    def embed_documents(self, texts):
        return self._encode(list(texts))

    def embed_query(self, text):
        return self._encode([text])[0]


@lru_cache(maxsize=2)
def get_local_embedder(path, device, python):
    return LocalEmbedder(path, device, python)
