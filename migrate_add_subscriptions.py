"""Migration script to add subscription system tables and remove is_approved fields.

This script:
1. Creates new tables: subscriptions, usage_tracking, payments, promo_codes, promo_code_usage
2. Migrates existing users to Free tier
3. Removes is_approved, approval_date, awaiting_verification columns from users table
4. Creates necessary indices

USAGE:
    python migrate_add_subscriptions.py

IMPORTANT: Backup your database before running!
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import inspect, text
from models.base import engine, Base
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

def backup_database():
    """Create a backup of the database before migration."""
    import shutil
    from pathlib import Path
    
   
    db_path = Path("sferatc_dev.db")
    if db_path.exists():
        backup_path = Path(f"sferatc_dev_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        shutil.copy2(db_path, backup_path)
        print(f"✅ Database backed up to: {backup_path}")
        return True
    print("⚠️  Database file not found, skipping backup")
    return False


def check_column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def drop_old_indices():
    """Drop old indices related to is_approved."""
    print("\n📌 Dropping old indices...")
    
    with engine.connect() as conn:
        try:
            # Drop is_approved related indices
            conn.execute(text("DROP INDEX IF EXISTS ix_user_last_seen_active"))
            conn.execute(text("DROP INDEX IF EXISTS ix_user_verification_status"))
            conn.commit()
            print("✅ Old indices dropped")
        except Exception as e:
            print(f"⚠️  Error dropping indices (may not exist): {e}")


def remove_old_columns():
    """Remove is_approved related columns from users table."""
    print("\n📌 Removing old columns from users table...")
    
    if not check_column_exists("users", "is_approved"):
        print("✅ Columns already removed, skipping")
        return
    
    with engine.connect() as conn:
        try:
            # SQLite doesn't support DROP COLUMN directly
            # Need to recreate table without those columns
            
            # 1. Create temp table with new schema
            conn.execute(text("""
                CREATE TABLE users_new (
                    id INTEGER PRIMARY KEY,
                    user_id BIGINT UNIQUE NOT NULL,
                    username VARCHAR,
                    full_name VARCHAR,
                    first_seen DATETIME,
                    last_seen DATETIME,
                    is_banned BOOLEAN DEFAULT 0
                )
            """))
            
            # 2. Copy data
            conn.execute(text("""
                INSERT INTO users_new (id, user_id, username, full_name, first_seen, last_seen, is_banned)
                SELECT id, user_id, username, full_name, first_seen, last_seen, is_banned
                FROM users
            """))
            
            # 3. Drop old table
            conn.execute(text("DROP TABLE users"))
            
            # 4. Rename new table
            conn.execute(text("ALTER TABLE users_new RENAME TO users"))
            
            # 5. Recreate indices
            conn.execute(text("CREATE INDEX ix_user_username_lower ON users (lower(username))"))
            conn.execute(text("CREATE INDEX ix_user_last_seen ON users (last_seen)"))
            conn.execute(text("CREATE INDEX ix_user_banned_status ON users (is_banned)"))
            conn.execute(text("CREATE UNIQUE INDEX ix_users_user_id ON users (user_id)"))
            
            conn.commit()
            print("✅ Old columns removed successfully")
        except Exception as e:
            print(f"❌ Error removing columns: {e}")
            conn.rollback()
            raise


def create_new_tables():
    """Create new subscription-related tables."""
    print("\n📌 Creating new tables...")
    
    # This will create all tables defined in Base.metadata
    Base.metadata.create_all(bind=engine)
    
    print("✅ New tables created:")
    print("   - subscriptions")
    print("   - usage_tracking")
    print("   - payments")
    print("   - promo_codes")
    print("   - promo_code_usage")


def migrate_existing_users():
    """Create Free tier subscriptions for all existing users."""
    print("\n📌 Migrating existing users to Free tier...")
    
    with get_db() as db:
        # Get all users without subscriptions
        users = db.query(User).outerjoin(Subscription).filter(Subscription.id == None).all()
        
        if not users:
            print("✅ No users to migrate")
            return
        
        print(f"Found {len(users)} users to migrate")
        
        for user in users:
            subscription = Subscription(
                user_id=user.user_id,
                tier="free",
                status="active",
                start_date=datetime.now(),
                expiry_date=None,  # Free tier never expires
                payment_method=None
            )
            db.add(subscription)
        
        db.commit()
        print(f"✅ Migrated {len(users)} users to Free tier")


def verify_migration():
    """Verify that migration was successful."""
    print("\n📌 Verifying migration...")
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    required_tables = ["subscriptions", "usage_tracking", "payments", "promo_codes", "promo_code_usage"]
    missing_tables = [t for t in required_tables if t not in tables]
    
    if missing_tables:
        print(f"❌ Missing tables: {missing_tables}")
        return False
    
    # Check users table doesn't have old columns
    users_columns = [col['name'] for col in inspector.get_columns("users")]
    
    if "is_approved" in users_columns:
        print("❌ is_approved column still exists in users table")
        return False
    
    # Check all users have subscriptions
    with get_db() as db:
        users_count = db.query(User).count()
        subs_count = db.query(Subscription).count()
        
        if users_count != subs_count:
            print(f"⚠️  Users count ({users_count}) doesn't match subscriptions count ({subs_count})")
            return False
    
    print("✅ Migration verification passed!")
    return True


def main():
    """Run the migration."""
    print("=" * 60)
    print("🚀 Starting Subscription System Migration")
    print("=" * 60)
    
    try:
        # Step 1: Backup
        if not backup_database():
            response = input("Continue without backup? (y/N): ")
            if response.lower() != 'y':
                print("Migration cancelled")
                return
        
        # Step 2: Drop old indices
        drop_old_indices()
        
        # Step 3: Remove old columns
        remove_old_columns()
        
        # Step 4: Create new tables
        create_new_tables()
        
        # Step 5: Migrate existing users
        migrate_existing_users()
        
        # Step 6: Verify
        if verify_migration():
            print("\n" + "=" * 60)
            print("✅ Migration completed successfully!")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("⚠️  Migration completed with warnings")
            print("=" * 60)
    
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("\nRestore from backup if needed")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
