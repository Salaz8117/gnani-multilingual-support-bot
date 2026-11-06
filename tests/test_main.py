from unittest.mock import patch

import pytest

from app.core.exceptions import ConfigurationError
from app.main import app, lifespan


@pytest.mark.parametrize("api_key", ["", "your_gnani_api_key_here"])
async def test_api_lifespan_rejects_missing_api_key(api_key):
    with patch("app.main.get_settings") as get_settings:
        get_settings.return_value.gnani_api_key = api_key

        with pytest.raises(ConfigurationError, match="GNANI_API_KEY"):
            async with lifespan(app):
                pass
