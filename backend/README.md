# Backend Structure

The FastAPI backend is organized by responsibility:

```text
backend/
  controllers/   HTTP response shaping and request orchestration
  routes/        FastAPI route registration and URL contracts
  services/      application operations and database/parser delegation
  schemas.py     shared request validation models
```

Current modular route groups:

- `auth_routes.py`: login and user access endpoints
- `drive_routes.py`: drive listing, creation, and result viewing
- `upload_routes.py`: shortlist, verdict, roster, user-access, and company-drive uploads

`app.py` remains the composition root and compatibility surface for existing imports. The SQLAlchemy ORM and database services remain in the project-level `db.py` and `orm_models.py` modules.
