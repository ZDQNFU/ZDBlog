import json
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from rag.evaluation import evaluate_cases
from rag.retriever import retrieve


class Command(BaseCommand):
    help = 'Evaluate article-level Recall@k, HitRate@k, MRR and negative accuracy'

    def add_arguments(self, parser):
        parser.add_argument('--gold', default=str(Path(settings.BASE_DIR).parent / 'docs' / 'rag_gold.jsonl'))
        parser.add_argument('--k', type=int, default=5)

    def handle(self, *args, **options):
        if not 1 <= options['k'] <= 20:
            raise CommandError('--k must be between 1 and 20')
        try:
            with open(options['gold'], encoding='utf-8') as file:
                cases = [json.loads(line) for line in file if line.strip()]
            if not cases or any(not isinstance(c.get('q'), str) or not isinstance(c.get('expect'), list) for c in cases):
                raise ValueError('Gold cases must contain q and expect')
        except (OSError, ValueError, AttributeError) as exc:
            raise CommandError(f'Cannot load gold dataset ({type(exc).__name__})') from None
        self.stdout.write(json.dumps(evaluate_cases(cases, retrieve, options['k']), ensure_ascii=False, indent=2))
