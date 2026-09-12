from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection


class ApplyRLS(BaseCommand):
    help = "Executes SQL to apply row level security policies on argument model"

    def add_arguments(self, parser):
        parser.add_argument("models", help="separate models with comma(,)")

    def handle(self, *args, **options):
        models_arg = options["models"].strip().split(",")

        for model in models_arg:
            try:
                try:
                    model_class = apps.get_model(app_label="core", model_name=model)
                except LookupError:
                    model_class = apps.get_model(app_label="chats", model_name=model)

                table_name = model_class._meta.db_table

                if hasattr(model_class, "tenant_id") or hasattr(model_class, "tenant"):
                    policy_condition = (
                        "tenant_id = current_setting('app.current_tenant', true)::UUID"
                    )
                elif hasattr(model_class, "room"):
                    policy_condition = "room_id IN (SELECT id FROM chats_chatrooms WHERE tenant_id = current_setting('app.current_tenant', true)::UUID)"
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipping {model}: No clear relation to tenant_id."
                        )
                    )
                    continue

                sql_command = [
                    f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;",
                    f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;",
                    f"DROP POLICY IF EXISTS {table_name}_tenant_policy ON {table_name};",
                    f"CREATE POLICY {table_name}_tenant_policy ON {table_name} FOR ALL USING ({policy_condition});",
                ]

                with connection.cursor() as cursor:
                    for sql in sql_command:
                        cursor.execute(sql)

                self.stdout.write(
                    self.style.SUCCESS(f"RLS successfully applied on {table_name}")
                )
            except LookupError:
                self.stdout.write(
                    self.style.ERROR(
                        f"Model '{model}' not found in 'core' or 'chats' apps."
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Failed to apply RLS on {model}\nError: {e}")
                )
