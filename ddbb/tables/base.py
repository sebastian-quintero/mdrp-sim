import datetime

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class TableModel:
    parameters = []

    def to_dict(self):
        return {param: self.get_parameter(param) for param in self.parameters}

    def get_parameter(self, parameter):
        if parameter == 'created_at' or parameter == 'updated_at':
            return str(datetime.datetime.now())
        return getattr(self, parameter)
