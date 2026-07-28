# Import all models so Alembic autogenerate can see them
from models.user import User                # noqa
from models.refresh_token import RefreshToken  # noqa
from models.password_reset_token import PasswordResetToken  # noqa
from models.job import Job                  # noqa
from models.saved_job import SavedJob       # noqa
from models.note import Note                # noqa
from models.profile import UserProfile      # noqa
from models.search_log import SearchLog     # noqa
from models.notification import Notification  # noqa
from models.application import JobApplication  # noqa
