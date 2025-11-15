
# write the code to prevent non-admins from accessing certain routes    
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.pg_models import User
from db.pg_connections import get_db
from api.routes.login import get_admin_user, bearer_scheme

def admin_required(current_user: User = Depends(get_admin_user),db: Session = Depends(get_db)):  
    # prevent non-admin users from accessing the route
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource."
        )
    return current_user