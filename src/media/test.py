import dropbox
from src.config import config


dbx = dropbox.Dropbox(
    oauth2_refresh_token=config.env_data.DROPBOX_REFRESH_TOKEN,
    app_key=config.env_data.DROPBOX_APP_KEY,
    app_secret=config.env_data.DROPBOX_APP_SECRET,
)

print(dbx.users_get_current_account().name.display_name)
