#!/usr/bin/env python3
"""
Migration to remove pricing_model and unit from MaterialUnterkategorie 
and ensure all variants have their own pricing information.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "catalog.db"

def migrate():
    """Remove pricing fields from subcategories and ensure variants have pricing data"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("Starting migration to remove subcategory pricing fields...")
        
        # First, add missing is_spende column to material_unterkategorie table
        print("Adding is_spende column to material_unterkategorie table...")
        
        cursor.execute("PRAGMA table_info(material_unterkategorie)")
        ukat_columns = [row[1] for row in cursor.fetchall()]
        
        if 'is_spende' not in ukat_columns:
            print("Adding is_spende column to material_unterkategorie...")
            cursor.execute("ALTER TABLE material_unterkategorie ADD COLUMN is_spende INTEGER DEFAULT 0")
        
        # Now add missing columns to material_variante table
        print("Adding missing columns to material_variante table...")
        
        cursor.execute("PRAGMA table_info(material_variante)")
        variant_columns = [row[1] for row in cursor.fetchall()]
        
        if 'pricing_model' not in variant_columns:
            print("Adding pricing_model column to material_variante...")
            cursor.execute("ALTER TABLE material_variante ADD COLUMN pricing_model TEXT DEFAULT 'per_unit'")
        
        if 'unit' not in variant_columns:
            print("Adding unit column to material_variante...")
            cursor.execute("ALTER TABLE material_variante ADD COLUMN unit TEXT")
        
        if 'tax_rate' not in variant_columns:
            print("Adding tax_rate column to material_variante...")
            cursor.execute("ALTER TABLE material_variante ADD COLUMN tax_rate REAL DEFAULT 19.0")
        
        if 'is_spende' not in variant_columns:
            print("Adding is_spende column to material_variante...")
            cursor.execute("ALTER TABLE material_variante ADD COLUMN is_spende INTEGER DEFAULT 0")
        
        # Now, ensure all variants have pricing_model, unit, tax_rate, and is_spende set
        # Copy from subcategory if variant doesn't have its own
        print("Migrating pricing data from subcategories to variants...")
        
        cursor.execute("""
            UPDATE material_variante 
            SET pricing_model = COALESCE(material_variante.pricing_model, material_unterkategorie.pricing_model, 'per_unit'),
                unit = COALESCE(material_variante.unit, material_unterkategorie.unit),
                tax_rate = COALESCE(material_variante.tax_rate, material_unterkategorie.tax_rate, 19.0),
                is_spende = COALESCE(material_variante.is_spende, material_unterkategorie.is_spende, 0)
            FROM material_unterkategorie 
            WHERE material_variante.unterkategorie_id = material_unterkategorie.id
            AND (material_variante.pricing_model IS NULL OR material_variante.unit IS NULL OR 
                 material_variante.tax_rate IS NULL OR material_variante.is_spende IS NULL)
        """)
        
        # Handle variants that are directly linked to kategorien (old format)
        cursor.execute("""
            UPDATE material_variante 
            SET pricing_model = COALESCE(material_variante.pricing_model, material_kategorie.pricing_model, 'per_unit'),
                unit = COALESCE(material_variante.unit, material_kategorie.unit),
                tax_rate = COALESCE(material_variante.tax_rate, material_kategorie.tax_rate, 19.0),
                is_spende = COALESCE(material_variante.is_spende, 0)
            FROM material_kategorie 
            WHERE material_variante.kategorie_id = material_kategorie.id 
            AND material_variante.unterkategorie_id IS NULL
            AND (material_variante.pricing_model IS NULL OR material_variante.unit IS NULL OR 
                 material_variante.tax_rate IS NULL OR material_variante.is_spende IS NULL)
        """)
        
        updated_variants = cursor.rowcount
        print(f"Updated {updated_variants} variants with pricing information")
        
        # Check if columns exist before dropping them from subcategories
        cursor.execute("PRAGMA table_info(material_unterkategorie)")
        ukat_columns = [row[1] for row in cursor.fetchall()]
        
        if 'pricing_model' in ukat_columns:
            print("Dropping pricing_model column from material_unterkategorie...")
            cursor.execute("ALTER TABLE material_unterkategorie DROP COLUMN pricing_model")
        
        if 'unit' in ukat_columns:
            print("Dropping unit column from material_unterkategorie...")
            cursor.execute("ALTER TABLE material_unterkategorie DROP COLUMN unit")
        
        # Also drop from material_kategorie if they exist (they're marked as vestigial)
        cursor.execute("PRAGMA table_info(material_kategorie)")
        kat_columns = [row[1] for row in cursor.fetchall()]
        
        if 'pricing_model' in kat_columns:
            print("Dropping pricing_model column from material_kategorie...")
            cursor.execute("ALTER TABLE material_kategorie DROP COLUMN pricing_model")
        
        if 'unit' in kat_columns:
            print("Dropping unit column from material_kategorie...")
            cursor.execute("ALTER TABLE material_kategorie DROP COLUMN unit")
        
        conn.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
