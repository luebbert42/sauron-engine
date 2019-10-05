from collections import OrderedDict
from typing import List, Dict, Callable, Union, Any, Type, Tuple
from .models import JobModel
from .parsers import DefaultParser
from .exporters import DefaultExporter

# imports novos
import inspect
from enum import Enum
import sys
from pydantic import BaseModel

class Engine:

    job_model_class: Type[JobModel] = JobModel
    parser_class: Type[DefaultParser] = DefaultParser
    exporter_class: Type[DefaultExporter] = DefaultExporter

    parsed_rule: List[JobModel] = []

    session: Dict[str, Any] = {}

    def __init__(
        self,
        context: Dict[str, Any] = None,
        job_model: Type[JobModel] = None,
        parser_class: Type[DefaultParser] = None,
        exporter_class: Type[DefaultExporter] = None,
    ):
        """
        - Sessions can be initialized with a context provided by the user
        - Job Model and Parser can be changed
        """
        if context:
            self.session = context

        if job_model:
            self.job_model_class = job_model

        if parser_class:
            self.parser_class = parser_class

        if exporter_class:
            self.exporter_class = exporter_class
        self.callables_collected: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()

    def _add_callable(
        self, function: Callable, verbose_name: str, job_type: str = "job"
    ):
        self.callables_collected[function.__name__] = {
            "function": function,
            "verbose_name": verbose_name,
            "type": job_type,
        }

    def job(self, *args, **kwargs):
        """
        Decorator so jobs can be called as follows:
        @obj.job
        def my_function():
            return None
        """

        def decorator(function: Callable):
            verbose_name: str = kwargs.get("verbose_name", None)
            if args:
                verbose_name = args[0]
            self._add_callable(function, verbose_name)
            return function

        return decorator

    @staticmethod
    def get_param_info(param):
        """
        Get Type and Defaults of the parameter. If the parameter is an Enum,
        also gets the choices available
        """
        annotation = param.annotation
        name = annotation

        choices = None
        if Enum in annotation.__mro__:
            choices = [choice for choice in annotation.__members__]
        defaults = param.default
        if defaults is param.empty:
            defaults = None
        return name, choices, defaults

    @classmethod
    def _get_function_metadata(
        cls, input_function: Callable
    ) -> Dict[str, Any]:
        """
            Metadata about arguments documentation and the function itself
        """
        signature: inspect.Signature = inspect.signature(input_function)
        arguments_metadata: Dict[str, Dict[str, Any]] = {}
        for key, parameter in signature.parameters.items():
            arg_type, arg_choices, arg_defaults = cls.get_param_info(parameter)
            arguments_metadata[key] = {
                "default": arg_defaults,
                "type": arg_type.__name__,
                "type_class": arg_type,
                "choices": arg_choices,
            }

        metadata = {
            "args": arguments_metadata,
            "doc": inspect.getdoc(input_function),
            "name": input_function.__name__,
        }

        return metadata


    def apply_job_call(
        self, job: JobModel, session: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Any]:
        target: Dict[str, Any] = self.callables_collected.get(job.name)

        target_func: Callable = target.get("function")
        target_func_variables: Dict[str, Any] = self._get_function_metadata(target_func)

        # Runs the job and captures result
        if job.args:

            # verifies if there is a pydantic model in the arguments if so instantiates it
            # and returns the object in place of the argument
            for key, value in job.args.items():
                key_data = target_func_variables["args"][key]
                if issubclass(key_data["type_class"],BaseModel):
                    job.args[key] = key_data["type_class"](**value)
            result = target_func(session=session, **job.args)
        else:
            result = target_func(session=session)

        # append result of function called into session
        results = session.get("results", None)
        if not results:
            session["results"] = []

        session["results"].append({"job": job.name, "return": result})
        self.session = session
        return (session, result)

    def parse(self, unparsed_rule: Union[str, Dict[str, Any]]):
        """
            Parses rules
        """
        parser: DefaultParser = self.parser_class()
        parsed_rule: List[JobModel] = parser.parse(unparsed_rule)
        self.parsed_rule = parsed_rule
        return parsed_rule

    def run(
        self, rule: Union[str, Dict[str, Any]], session: Dict[str, Any] = None
    ):
        """
        Executes each job passing the current session to them
        """

        if not session:
            session = self.session

        for job in self.parse(rule):
            session, result = self.apply_job_call(job, session)
            if not result:
                break

    def export_metadata(self, fmt: str = "dict"):
        exporter = self.exporter_class()
        return exporter.export_jobs(self.callables_collected, fmt=fmt)
