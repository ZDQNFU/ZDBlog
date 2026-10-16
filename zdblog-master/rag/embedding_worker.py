"""Private newline-JSON worker. Model weights are loaded once, strictly offline."""
import contextlib
import json
import os
import sys

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'


def main():
    model = None
    for line in sys.stdin:
        try:
            request = json.loads(line)
            with contextlib.redirect_stdout(sys.stderr):
                if model is None:
                    from sentence_transformers import SentenceTransformer
                    import torch
                    torch.set_num_threads(min(4, os.cpu_count() or 1))
                    model = SentenceTransformer(sys.argv[1], device=sys.argv[2], local_files_only=True)
                vectors = model.encode(request['texts'], normalize_embeddings=True,
                                       show_progress_bar=False, batch_size=16).tolist()
            response = {'vectors': vectors}
        except Exception as exc:
            response = {'error': type(exc).__name__}
        print(json.dumps(response), flush=True)


if __name__ == '__main__':
    main()
