"""PostgreSQL migration script for subscription system.

This script adds subscription tables and removes is_approved fields.
Designed for PostgreSQL production database.

USAGE:
    python migrate_postgresql.py
    
REQUIREMENTS:
    - PostgreSQL database
    - DATABASE_URL environment variable set
    - psycopg2 installed

IMPORTANT: Backup your database before running!
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text, inspect
from models.base import engine
from models import (
    User,
    Subscription,
    UsageTracking,
    Payment,
    PromoCode,
    PromoCodeUsage,
)
from db_session import get_db
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_database_type():
    """Verify we're running on PostgreSQL."""
    db_url = str(engine.url)
    if not db_url.startswith('postgresql'):
        logger.error(f"This script is for PostgreSQL only. Current DB: {db_url}")
        sys.exit(1)
    logger.info(f"✅ Confirmed PostgreSQL database")


def create_new_tables():
    """Create subscription-related tables."""
    logger.info("\n📌 Creating new tables...")
    
    from models.base import Base
    
    # Create only new tables (skip existing ones)
    tables_to_create = [
        Subscription.__table__,
        UsageTracking.__table__,
        Payment.__table__,
        PromoCode.__table__,
        PromoCodeUsage.__table__,
    ]
    
    for table in tables_to_create:
        try:
            table.create(bind=engine, checkfirst=True)
            logger.info(f"   ✅ Created table: {table.name}")
        except Exception as e:
            logger.warning(f"   ⚠️  Table {table.name} may already exist: {e}")
    
    logger.info("✅ New tables created")


def drop_old_columns():
    """Remove is_approved related columns from users table."""
    logger.info("\n📌 Removing old columns from users table...")
    
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    columns_to_drop = ['is_approved', 'approval_date', 'awaiting_verification']
    
    with engine.begin() as conn:
        for column in columns_to_drop:
            if column in columns:
                try:
                    conn.execute(text(f"ALTER TABLE users DROP COLUMN {column}"))
                    logger.info(f"   ✅ Dropped column: {column}")
                except Exception as e:
                    logger.warning(f"   ⚠️  Could not drop {column}: {e}")
            else:
                logger.info(f"   ℹ️  Column {column} does not exist, skipping")
    
    logger.info("✅ Old columns removed")


def drop_old_indices():
    """Drop old indices related to is_approved."""
    logger.info("\n📌 Dropping old indices...")
    
    with engine.begin() as conn:
        indices_to_drop = [
            'ix_user_last_seen_active',
            'ix_user_verification_status',
        ]
        
        for index_name in indices_to_drop:
            try:
                conn.execute(text(f"DROP INDEX IF EXISTS {index_name}"))
                logger.info(f"   ✅ Dropped index: {index_name}")
            except Exception as e:
                logger.warning(f"   ⚠️  Could not drop index {index_name}: {e}")
    
    logger.info("✅ Old indices dropped")


def create_new_indices():
    """Create new indices for users table."""
    logger.info("\n📌 Creating new indices...")
    
    with engine.begin() as conn:
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_user_last_seen ON users (last_seen)"))
            logger.info("   ✅ Created index: ix_user_last_seen")
        except Exception as e:
            logger.warning(f"   ⚠️  Index creation warning: {e}")
    
    logger.info("✅ New indices created")


def migrate_existing_users():
    """Create Free tier subscriptions for all existing users."""
    logger.info("\n📌 Migrating existing users to Free tier...")
    
    with get_db() as db:
        # Count users without subscriptions
        users = db.execute(text("""
            SELECT u.user_id 
            FROM users u 
            LEFT JOIN subscriptions s ON u.user_id = s.user_id 
            WHERE s.id IS NULL
        """)).fetchall()
        
        if not users:
            logger.info("✅ No users to migrate")
            return
        
        logger.info(f"Found {len(users)} users to migrate")
        
        # Create subscriptions in batch
        for row in users:
            user_id = row[0]
            db.execute(text("""
                INSERT INTO subscriptions (user_id, tier, status, start_date, expiry_date)
                VALUES (:user_id, 'free', 'active', :now, NULL)
            """), {"user_id": user_id, "now": datetime.now()})
        
        db.commit()
        logger.info(f"✅ Migrated {len(users)} users to Free tier")


def verify_migration():
    """Verify that migration was successful."""
    logger.info("\n📌 Verifying migration...")
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    required_tables = ["subscriptions", "usage_tracking", "payments", "promo_codes", "promo_code_usage"]
    missing_tables = [t for t in required_tables if t not in tables]
    
    if missing_tables:
        logger.error(f"❌ Missing tables: {missing_tables}")
        return False
    
    # Check users table doesn't have old columns
    users_columns = [col['name'] for col in inspector.get_columns("users")]
    
    if "is_approved" in users_columns:
        logger.error("❌ is_approved column still exists in users table")
        return False
    
    # Check all users have subscriptions
    with get_db() as db:
        result = db.execute(text("""
            SELECT 
                (SELECT COUNT(*) FROM users) as users_count,
                (SELECT COUNT(*) FROM subscriptions) as subs_count
        """)).fetchone()
        
        users_count, subs_count = result
        
        if users_count != subs_count:
            logger.warning(f"⚠️  Users count ({users_count}) doesn't match subscriptions count ({subs_count})")
            return False
    
    logger.info("✅ Migration verification passed!")
    return True


def main():
    """Run the PostgreSQL migration."""
    logger.info("=" * 60)
    logger.info("🚀 Starting PostgreSQL Subscription System Migration")
    logger.info("=" * 60)
    
    try:
        # Step 1: Verify PostgreSQL
        check_database_type()
        
        # Step 2: Confirm with user
        print("\n⚠️  IMPORTANT: This will modify your production database!")
        print("   Make sure you have a backup before proceeding.")
        response = input("\nContinue with migration? (yes/no): ")
        
        if response.lower() != 'yes':
            logger.info("Migration cancelled by user")
            return
        
        # Step 3: Drop old indices
        drop_old_indices()
        
        # Step 4: Create new tables
        create_new_tables()
        
        # Step 5: Migrate existing users
        migrate_existing_users()
        
        # Step 6: Remove old columns
        drop_old_columns()
        
        # Step 7: Create new indices
        create_new_indices()
        
        # Step 8: Verify
        if verify_migration():
            logger.info("\n" + "=" * 60)
            logger.info("✅ Migration completed successfully!")
            logger.info("=" * 60)
        else:
            logger.error("\n" + "=" * 60)
            logger.error("⚠️  Migration completed with warnings")
            logger.error("=" * 60)
    
    except Exception as e:
        logger.error(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
