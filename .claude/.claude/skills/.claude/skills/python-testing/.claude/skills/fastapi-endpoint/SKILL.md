---
name: fastapi-endpoint
description: Use when creating or modifying FastAPI routes, endpoints, or API handlers. Triggers on requests involving REST endpoints, route handlers, request/response models, or API versioning.
---

# FastAPI Endpoint

## Structure
- Routers in `app/api/v1/<resource>.py`, one router per resource
- Use `APIRouter(prefix="/resource", tags=["resource"])`
- Dependencies via `Depends()`, never instantiate services in handler body
- Pydantic v2 models: `<Resource>Create`, `<Resource>Update`, `<Resource>Read` in `app/schemas/`

## Handler rules
- Async by default
- Thin handlers: parse → call service → return. No business logic.
- Explicit `response_model` and `status_code` on every route
- Raise `HTTPException` only at router layer; services raise domain exceptions

## Example pattern
```python
@router.post("/", response_model=UserRead, status_code=201)
async def create_user(
    payload: UserCreate,
    service: UserService = Depends(get_user_service),
) -> UserRead:
    try:
        return await service.create(payload)
    except UserAlreadyExists as e:
        raise HTTPException(409, str(e))
```

## Validation
- Use Pydantic validators, not manual checks in handlers
- Path/query params typed with `Annotated[int, Path(ge=1)]`