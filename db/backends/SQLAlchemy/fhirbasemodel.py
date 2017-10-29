from sqlalchemy_pagination import paginate

import settings
from .abstractbasemodel import AbstractBaseModel

## TODO: I'm pretty sure this shouldn't be happening here
from Fhir.resources import PaginatedBundle

class FhirBaseModel(AbstractBaseModel):
  __abstract__ = True

  @classmethod
  def get(cls, query, *args, **kwargs):
    '''
    Handle a GET request
    '''
    if query.resourceId:
      item = cls.query.get(query.resourceId)
      res = item.to_fhir(query, *args, **kwargs)
      return res.as_json()

    else:
      count = int(query.modifiers.get('_count', [settings.DEFAULT_BUNDLE_SIZE])[0])
      count = min(count, settings.MAX_BUNDLE_SIZE)
      offset = query.search_params.get('search-offset', ['1'])
      offset = int(offset[0])
      pagination = paginate(cls.query, offset, offset+count)
      params = {
          'items': [item.to_fhir(query, *args, **kwargs) for item in pagination.items],
          'total': pagination.total,
          'pages': pagination.pages,
          'has_next': pagination.has_next,
          'has_previous': pagination.has_previous,
          'next_page': f'{cls.__name__}/?_count={count}&search-offset={offset+count}',
          'previous_page': f'{cls.__name__}/?_count={count}&search-offset={max(offset-count,1)}',
      }
      return PaginatedBundle(pagination=params).as_json()