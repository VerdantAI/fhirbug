import isodate
import calendar
from datetime import timedelta, datetime
from sqlalchemy import or_, not_, and_
from fhirbug.exceptions import QueryValidationError
from fhirbug.utils import date_ceil, transform_date


def to_float(str):
    try:
        return float(str)
    except ValueError:
        raise QueryValidationError("{} is an invalid numerical parameter".format(str))


def NumericSearch(column):
    def search(cls, field_name, value, sql_query, query):
        col = getattr(cls, column)
        if value.startswith("lt"):  # Less than
            return sql_query.filter(col < to_float(value[2:]))
        if value.startswith("gt"):  # Greater than
            return sql_query.filter(col > to_float(value[2:]))
        if value.startswith("le"):  # Less or equal
            return sql_query.filter(col <= to_float(value[2:]))
        if value.startswith("ge"):  # Greater or equal
            return sql_query.filter(col >= to_float(value[2:]))
        if value.startswith("eq"):  # Equals
            return sql_query.filter(col == to_float(value[2:]))
        if value.startswith("ne"):  # Not Equal
            return sql_query.filter(col != to_float(value[2:]))
        if value.startswith("ap"):  # Approximately (+- 10%)
            val = to_float(value[2:])
            return sql_query.filter(col >= val - val * 0.1).filter(
                col <= val + val * 0.1
            )

        return sql_query.filter(col == to_float(value))

    return search


def NumericSearchWithQuantity(column, convert_value=None, alter_query=None):
    def search(cls, field_name, value, sql_query, query):
        parts = value.split("|", 1)
        if len(parts) == 2:
            value, quantity = parts
            if convert_value:
                value = convert_value(value, quantity)
            if alter_query:
                sql_query = alter_query(query, value, quantity)
        return NumericSearch(column).search(cls, field_name, value, sql_query, query)

    return search


def DateSearch(column):
    def search_datetime(cls, field_name, value, sql_query, query):
        # value = query.search_params[field_name] if field_name in query.search_params else query.modifiers[field_name]
        # value = value.pop()
        col = getattr(cls, column)
        if value.startswith("lt"):  # Less than
            return sql_query.filter(col < transform_date(value))
        if value.startswith("gt"):  # Greater than
            return sql_query.filter(col > date_ceil(value))
        if value.startswith("le"):  # Less or equal
            return sql_query.filter(col <= date_ceil(value))
        if value.startswith("ge"):  # Greater or equal
            return sql_query.filter(col >= transform_date(value))
        if value.startswith("eq"):  # Equals
            return sql_query.filter(
            (col >= transform_date(value)),
            (col <= date_ceil(value)),
)
        if value.startswith("ne"):  # Not Equal
            return sql_query.filter(not_(and_(
            (col >= transform_date(value)),
            (col <= date_ceil(value)),
)))
        ## TODO load from settings
        if value.startswith("ap"):  # Approximately (+- 1month)
            floor = transform_date(value) - timedelta(30)
            ceil = transform_date(value) + timedelta(30)
            return sql_query.filter(col >= floor).filter(col <= ceil)

        return sql_query.filter(
        (col >= transform_date(value, trim=False)),
        (col <= date_ceil(value, trim=False)),
)

    return search_datetime


def StringSearch(*column_names):
    """
  Search for string types, supports :contains and :exact modifiers.

  If string search should be performed in multiple columns using OR
  multiple columns can be passed.
  """
    if len(column_names) == 0:
        raise TypeError("StringSearch takes at least one positional argument (0 given)")

    def search(cls, field_name, value, sql_query, query):
        columns = [getattr(cls, column) for column in column_names]
        if ":contains" in field_name:
            # value = value.replace(':contains', '')
            return sql_query.filter(or_(col.contains(value) for col in columns))
        if ":exact" in field_name:
            # value = value.replace(':exact', '')
            return sql_query.filter(or_(col == value for col in columns))
        return sql_query.filter(or_(col.startswith(value) for col in columns))

    return search


def NameSearch(column):
    def search_name(cls, field_name, value, sql_query, query):
        # value = query.search_params[field_name] if field_name in query.search_params else query.modifiers[field_name]
        # value = value.pop()
        col = getattr(cls, column)
        # if value.startswith('lt'):  # Less than
        #   return sql_query.filter(col < value[2:])
        # if value.startswith('gt'):  # Greater than
        #   return sql_query.filter(col > value[2:])
        # if value.startswith('le'):  # Less or equal
        #   return sql_query.filter(col <= value[2:])
        # if value.startswith('ge'):  # Greater or equal
        #   return sql_query.filter(col >= value[2:])
        # if value.startswith('eq'):  # Equals
        #   return sql_query.filter(col == value[2:])
        # if value.startswith('ne'):  # Not Equal
        #   return sql_query.filter(col != value[2:])
        # if value.startswith('ap'):  # Approximately (+- 10%)
        #   val = float(value[2:])
        #   return sql_query.filter(col >= val-val*0.1).filter(col <= val+val*0.1)

        return sql_query.filter(col.contains(value))

    return search_name


def SimpleSearch(column):
    def search(cls, field_name, value, sql_query, query):
        col = getattr(cls, column)
        return sql_query.filter(col == value)

    return search
