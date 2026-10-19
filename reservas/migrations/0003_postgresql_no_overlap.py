from django.db import migrations


def install(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
        schema_editor.execute("""
            ALTER TABLE reservas_reservation ADD CONSTRAINT reservation_no_overlap
            EXCLUDE USING gist (
                room_id WITH =,
                daterange(start, \"end\", '[)') WITH &&
            ) WHERE (status IN ('pending', 'confirmed', 'in_house'))
        """)


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("ALTER TABLE reservas_reservation DROP CONSTRAINT IF EXISTS reservation_no_overlap")


class Migration(migrations.Migration):
    dependencies = [("reservas", "0002_initial")]
    operations = [migrations.RunPython(install, uninstall)]
