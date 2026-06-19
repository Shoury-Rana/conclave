from django.core.management.base import BaseCommand
from django.apps import apps


class ApplyRLS(BaseCommand):
    help = 'Executes SQL to apply row level security policies on argument model'

    def add_arguments(self, parser):
        parser.add_argument('models', help='separate models with comma(,)')

    def handle(self, *args, **options):
        models = options['models'].strip().split(',')

        for model in models:
            try:
                model_class = apps.get_model(app_label='core', model_name=model)
                table_name = model_class._meta.db_table

                sql_command = [
                    f'ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;',
                    f'ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;',
                    f'CREATE POLICY {table_name}_tenant_policy ON {table_name} FOR ALL\
                        USING (tenant_id = current_setting("app.current_tenant", true)::UUID);'
                ]

                self.stdout.write(self.style.SUCCESS(f'RLS successfully applied on {table_name}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'failed to apply RLS\nError: {e}'))