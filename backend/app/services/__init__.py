"""Service layer of the MVC structure: business logic, free of HTTP concerns
except raising ``HTTPException`` for domain rule violations (FastAPI-native
error channel), so controllers stay thin."""
