#!/usr/bin/env python3
"""
Migration script to import CSV data into PostgreSQL database.

This script:
1. Reads ai_tools.csv
2. Creates database tables
3. Imports all tools into the ai_tools table
4. Verifies the import

Usage:
    python scripts/migrate_csv_to_db.py
"""

import sys
import os
import pandas as pd
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from db.pg_connections import engine, init_db, get_db_info
from db.pg_models import AITool, Base
from sqlalchemy.orm import Session


def load_csv_data(csv_path: str) -> pd.DataFrame:
    """
    Load and validate CSV data.
    
    Args:
        csv_path: Path to ai_tools.csv
        
    Returns:
        DataFrame with CSV data
    """
    print(f"\n📂 Loading CSV from: {csv_path}")
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    df = pd.read_csv(csv_path)
    print(f"✓ Loaded {len(df)} tools from CSV")
    print(f"  Columns: {', '.join(df.columns)}")
    
    return df


def parse_ratings(ratings_str) -> float:
    """
    Parse ratings string to float.
    
    Examples:
        "Rated 4.5 out of 5" -> 4.5
        "Rated 0 out of 5" -> 0.0
        
    Args:
        ratings_str: Rating string from CSV
        
    Returns:
        Float rating value
    """
    if pd.isna(ratings_str) or not ratings_str:
        return 0.0
    
    try:
        # Extract number after "Rated"
        parts = str(ratings_str).split()
        if len(parts) >= 2 and parts[0] == "Rated":
            return round(float(parts[1]), 2)
    except (ValueError, IndexError):
        pass
    
    return 0.0


def import_tools_to_db(df: pd.DataFrame, session: Session) -> int:
    """
    Import tools from DataFrame to database.
    
    Args:
        df: DataFrame with tool data
        session: Database session
        
    Returns:
        Number of tools imported
    """
    print("\n🔄 Importing tools to database...")
    
    imported_count = 0
    skipped_count = 0
    error_count = 0
    
    for idx, row in df.iterrows():
        try:
            # Check if tool already exists
            existing = session.query(AITool).filter_by(name=row['name']).first()
            if existing:
                print(f"  ⏭️  Skipped (exists): {row['name']}")
                skipped_count += 1
                continue
            
            # Parse ratings
            ratings_value = parse_ratings(row.get('ratings', 0))
            
            # Create new AITool instance - import one by one to catch errors
            tool = AITool(
                name=str(row['name'])[:255],  # Ensure within VARCHAR limit
                url=str(row.get('url', ''))[:255],
                description=str(row.get('description', '')),
                summary=str(row.get('summary', '')),
                main_category=str(row.get('main_category', ''))[:100],
                sub_category=str(row.get('sub_category', ''))[:100],
                ai_categories=str(row.get('ai_categories', '')),
                pricing=str(row.get('pricing', '')),
                ratings=ratings_value,
                key_features=str(row.get('key_features', '')),
                pros=str(row.get('pros', '')),
                cons=str(row.get('cons', '')),
                who_should_use=str(row.get('who_should_use', '')),
                compatibility_integration=str(row.get('compatibility_integration', '')),
            )
            
            session.add(tool)
            # Commit immediately for each tool to avoid batch errors
            session.commit()
            imported_count += 1
            
            # Progress indicator every 10 tools
            if imported_count % 10 == 0:
                print(f"  ✓ Imported {imported_count} tools...")
        
        except Exception as e:
            error_count += 1
            print(f"  ❌ Error importing {row.get('name', 'Unknown')}: {str(e)[:100]}")
            session.rollback()
            # Continue with next tool instead of stopping
            continue
    
    print(f"\n✅ Import complete!")
    print(f"   ✓ Imported: {imported_count} tools")
    print(f"   ⏭️  Skipped: {skipped_count} tools (already exist)")
    print(f"   ❌ Errors: {error_count} tools (failed to import)")
    
    return imported_count


def verify_import(session: Session, expected_count: int):
    """
    Verify that import was successful.
    
    Args:
        session: Database session
        expected_count: Expected number of tools
    """
    print("\n🔍 Verifying import...")
    
    actual_count = session.query(AITool).count()
    print(f"  Tools in database: {actual_count}")
    
    if actual_count >= expected_count:
        print("  ✅ Verification passed!")
    else:
        print(f"  ⚠️  Warning: Expected {expected_count}, found {actual_count}")
    
    # Show sample tools
    print("\n📋 Sample tools:")
    sample_tools = session.query(AITool).limit(5).all()
    for tool in sample_tools:
        print(f"  • {tool.name} ({tool.main_category}) - Rating: {tool.ratings}")


def main():
    """Main migration function"""
    print("=" * 70)
    print("🚀 AI Tools CSV to PostgreSQL Migration")
    print("=" * 70)
    
    # Show database info
    db_info = get_db_info()
    print(f"\n📊 Database: {db_info['type']}")
    print(f"   Connection: {db_info['url']}")
    
    # CSV path
    csv_path = os.path.join(PROJECT_ROOT, "ai", "data", "ai_tools.csv")
    
    try:
        # Step 1: Load CSV
        df = load_csv_data(csv_path)
        
        # Step 2: Initialize database (create tables)
        print("\n🔨 Creating database tables...")
        init_db()
        
        # Step 3: Import data
        from db.pg_connections import SessionLocal
        session = SessionLocal()
        
        try:
            imported = import_tools_to_db(df, session)
            
            # Step 4: Verify
            verify_import(session, len(df))
            
        finally:
            session.close()
        
        print("\n" + "=" * 70)
        print("✅ Migration completed successfully!")
        print("=" * 70)
        print("\nNext steps:")
        print("  1. Update your code to use db.pg_connections instead of CSV")
        print("  2. Test the API endpoints")
        print("  3. Deploy to Render with DATABASE_URL environment variable")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
