# init_db.py — run once before starting the app
from db import create_tables, seed_tasks, seed_users, list_all_tasks, list_all_users
from ml_engine import seed_demo_pick_log

print("Setting up database...")
create_tables()
seed_tasks()
seed_users()
seed_demo_pick_log()

print("\nAccounts:")
for u in list_all_users():
    print(f"  {u['role']:12s}  {u['username']:15s}  {u['full_name']}")

print("\nTasks:")
for t in list_all_tasks():
    print(f"  {t['sequence_no']}. {t['location']:<8} code={t['confirm_code']:<4} qty={t['products']}")

print("\nDone. Run: python main.py")
