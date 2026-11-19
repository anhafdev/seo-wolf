from seowolf.storage import models_crawls, models_pages, models_projects, models_resources
from seowolf.storage.models_base import Base

__author__ = "@anhafxd"

MODEL_MODULES = (models_projects, models_crawls, models_pages, models_resources)
schema_metadata = Base.metadata
