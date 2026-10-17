from django.db import migrations, models
import pgvector.django.vector


class Migration(migrations.Migration):

    dependencies = [
        ('rag', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=[
                        "UPDATE article_chunk SET embedding = NULL, embedded_at = NULL, embed_fingerprint = ''",
                        "UPDATE article_rag_state SET status = 'pending', embed_fingerprint = '', indexed_at = NULL",
                        'ALTER TABLE article_chunk ALTER COLUMN embedding TYPE vector(1024) USING NULL::vector(1024)',
                    ],
                    reverse_sql=[
                        "UPDATE article_chunk SET embedding = NULL, embedded_at = NULL, embed_fingerprint = ''",
                        "UPDATE article_rag_state SET status = 'pending', embed_fingerprint = '', indexed_at = NULL",
                        'ALTER TABLE article_chunk ALTER COLUMN embedding TYPE vector(512) USING NULL::vector(512)',
                    ],
                ),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name='articlechunk',
                    name='embedding',
                    field=pgvector.django.vector.VectorField(blank=True, dimensions=1024, null=True),
                ),
            ],
        ),
    ]
