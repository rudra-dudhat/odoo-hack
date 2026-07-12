from typing import Callable, TypeVar, Any
from google.cloud import firestore
from src.infrastructure.firestore.client import db

T = TypeVar("T")

@firestore.transactional
def _execute_in_transaction(transaction: firestore.Transaction, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Helper decorated with @firestore.transactional to auto-retry on contention."""
    return func(transaction, *args, **kwargs)

def run_in_transaction(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """
    Run a function within a Firestore transaction.
    The function 'func' must take 'transaction' as its first argument:
      def my_func(transaction, ...):
          # read-then-write logic using transaction.get() and transaction.set()
    """
    transaction = db.transaction()
    return _execute_in_transaction(transaction, func, *args, **kwargs)

def get_write_batch() -> firestore.WriteBatch:
    """Return a new Firestore WriteBatch instance for atomic bulk writes."""
    return db.batch()
