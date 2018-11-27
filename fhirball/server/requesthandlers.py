from fhirball.server.requestparser import parse_url
from fhirball.exceptions import (
    MappingValidationError,
    QueryValidationError,
    ConfigurationError,
    OperationError,
)

from fhirball.Fhir.resources import OperationOutcome, FHIRValidationError
from fhirball.config import import_models, settings


def handle_get_request(url):
    """
    DEPRECATED. Use :class:`GetRequestHandler`
    Receive a request url as a string and handle it. This includes parsing the string into a
    :class:`fhirball.server.requestparser.FhirRequestQuery`, finding the model for the requested
    resource and calling `Resource.get` on it.
    It returns a tuple (response json, status code).
    If an error occurs during the process, an OperationOutcome is returned.

    :param url: a string containing the path of the request. It should not contain the server
                path. For example: `Patients/123?name:contains=Jo`
    :returns: (response json, status code) Where response_json may be the requested resource,
              a Bundle or an OperationOutcome in case of an error.

    """
    # Try to parse the url
    try:
        query = parse_url(url)
    except QueryValidationError as e:
        op = OperationOutcome(
            {
                "issue": [
                    {"severity": "error", "code": "bad-request", "diagnostics": f"{e}"}
                ]
            }
        )
        return op.as_json(), 400

    resource = query.resource
    try:
        models = import_models()
    except ConfigurationError:
        op = OperationOutcome(
            {
                "issue": [
                    {
                        "severity": "error",
                        "code": "server-error",
                        "diagnostics": f"The server is improprly configured",
                    }
                ]
            }
        )
        return op.as_json(), 500

    # Try to import the resource map class
    try:
        Resource = getattr(models, resource)
    except Exception:
        op = OperationOutcome(
            {
                "issue": [
                    {
                        "severity": "error",
                        "code": "not-found",
                        "diagnostics": f'Resource type "{resource}" does not exist or is not supported.',
                    }
                ]
            }
        )
        return op.as_json(), 404

    # Try to fetch the requested resource(s)
    try:
        res = Resource.get(query=query)
        return res, 200
    except (MappingValidationError, FHIRValidationError) as e:
        op = OperationOutcome(
            {
                "issue": [
                    {"severity": "error", "code": "not-found", "diagnostics": f"{e}"}
                ]
            }
        )
        return op.as_json(), 404
    except Exception as e:
        op = OperationOutcome(
            {
                "issue": [
                    {"severity": "error", "code": "server-error", "diagnostics": f"{e}"}
                ]
            }
        )
        import traceback

        print(traceback.format_exc())
        return op.as_json(), 500


def handle_post_request(url, body):
    """
    Receive a request url and the request body of a POST request and handle it. This includes parsing the string into a
    :class:`fhirball.server.requestparser.FhirRequestQuery`, finding the model for the requested
    resource and creating a new instance.
    It returns a tuple (response json, status code).
    If an error occurs during the process, an OperationOutcome is returned.

    :param url: a string containing the path of the request. It should not contain the server
                path. For example: `Patients/123?name:contains=Jo`
    :type url: string
    :param body: a dictionary containing all data that was sent with the request
    :type body: dict

    :returns: A tuple ``(response_json, status code)``, where response_json may be the requested resource,
              a Bundle or an OperationOutcome in case of an error.
    :rtype: tuple

    """
    query = parse_url(url)
    resource_name = query.resource

    try:
        models = import_models()
    except ConfigurationError:
        op = OperationOutcome(
            {
                "issue": [
                    {
                        "severity": "error",
                        "code": "server-error",
                        "diagnostics": f"The server is improprly configured",
                    }
                ]
            }
        )
        return op.as_json(), 500

    # Get the Resource
    try:
        from fhirball.Fhir import resources

        Resource = getattr(resources, resource_name)
    except Exception as e:
        op = OperationOutcome(
            {
                "issue": [
                    {
                        "severity": "error",
                        "code": "not-found",
                        "diagnostics": f'Resource "{resource_name}" does not exist.',
                    }
                ]
            }
        )
        return op.as_json(), 404

    # Validate the incoming json
    try:
        resource = Resource(body)
    except Exception as e:
        op = OperationOutcome(
            {
                "issue": [
                    {"severity": "error", "code": "validation", "diagnostics": f"{e}"}
                ]
            }
        )
        return op.as_json(), 400
    # Import the model
    try:
        Model = getattr(models, resource_name)
    except Exception as e:
        return {"error": "This shouldn't happen", "exception": str(e)}, 404

    try:
        new_resource = Model.create_from_resource(resource, query=query)
    except Exception as e:
        if settings.DEBUG:
            import traceback

            print(traceback.format_exc())
            op = OperationOutcome(
                {
                    "issue": [
                        {
                            "severity": "error",
                            "code": "validation",
                            "diagnostics": traceback.format_exc(),
                        }
                    ]
                }
            )
        else:
            op = OperationOutcome(
                {
                    "issue": [
                        {
                            "severity": "error",
                            "code": "validation",
                            "diagnostics": f"{e}",
                        }
                    ]
                }
            )

        return op.as_json(), 422
    # new_resource.save()
    return new_resource.to_fhir().as_json(), 201


class RequestHandler:
    def parse_url(self, url):
        try:
            self.query = parse_url(url)
        except QueryValidationError as e:
            raise OperationError(
                severity="error",
                code="invalid",
                diagnostics="{}".format(e),
                status_code=400,
            )

    def import_models(self):
        try:
            models = import_models()
        except ConfigurationError:
            raise OperationError(
                severity="error",
                code="exception",
                diagnostics="The server is improprly configured",
                status_code=500,
            )
        return models

    def get_resource(self, models):
        resource_name = self.query.resource
        try:
            Resource = getattr(models, resource_name)
        except AttributeError:
            raise OperationError(
                severity="error",
                code="not-found",
                diagnostics=f'Resource "{resource_name}" does not exist.',
                status_code=404,
            )
        return Resource


class GetRequestHandler(RequestHandler):
    """
    Receive a request url as a string and handle it. This includes parsing the string into a
    :class:`fhirball.server.requestparser.FhirRequestQuery`, finding the model for the requested
    resource and calling `Resource.get` on it.
    It returns a tuple (response json, status code).
    If an error occurs during the process, an OperationOutcome is returned.

    :param url: a string containing the path of the request. It should not contain the server
                path. For example: `Patients/123?name:contains=Jo`
    :returns: (response json, status code) Where response_json may be the requested resource,
              a Bundle or an OperationOutcome in case of an error.

    """
    def handle(self, url):
        try:
            self.parse_url(url)
            # Import the model mappings
            models = self.import_models()
            # Get the Resource
            Model = self.get_resource(models)
            # Validate the incoming json and instantiate the Fhir resource
            return self.fetch_items(Model)

        except OperationError as e:
            return e.to_fhir().as_json(), e.status_code

    def fetch_items(self, Model):
        # Try to fetch the requested resource(s)
        try:
            res = Model.get(query=self.query)
            return res, 200
        except (MappingValidationError, FHIRValidationError) as e:
            raise OperationError(
                severity="error",
                code="not-found",
                diagnostics="{}".format(e),
                status_code=404,
            )
        except Exception as e:
            diag = "{}".format(e)
            if settings.DEBUG:
                import traceback

                tb = traceback.format_exc()
                diag += " {}".format(tb)
            raise OperationError(
                severity="error",
                code="exception",
                diagnostics="{}".format(diag),
                status_code=500,
            )

class PostRequestHandler(RequestHandler):
    """
    Receive a request url and the request body of a POST request and handle it. This includes parsing the string into a
    :class:`fhirball.server.requestparser.FhirRequestQuery`, finding the model for the requested
    resource and creating a new instance.
    It returns a tuple (response json, status code).
    If an error occurs during the process, an OperationOutcome is returned.

    :param url: a string containing the path of the request. It should not contain the server
                path. For example: `Patients/123?name:contains=Jo`
    :type url: string
    :param body: a dictionary containing all data that was sent with the request
    :type body: dict

    :returns: A tuple ``(response_json, status code)``, where response_json may be the requested resource,
              a Bundle or an OperationOutcome in case of an error.
    :rtype: tuple

    """
    def handle(self, url, body):
        try:
            self.body = body
            self.parse_url(url)
            # Import the model mappings
            models = self.import_models()
            # Get the Model class
            Model = self.get_resource(models)

            from fhirball.Fhir import resources
            # Get the Resource class
            Resource = self.get_resource(resources)
            # Validate the incoming json and instantiate the Fhir resource
            resource = self.request_body_to_resource(Resource)

            created_resource = self.create(Model, resource)
            return created_resource.to_fhir().as_json(), 201

        except OperationError as e:
            return e.to_fhir().as_json(), e.status_code

    def request_body_to_resource(self, Resource):
        # Validate the incoming json
        try:
            resource = Resource(self.body)
            return resource
        except Exception as e:
            raise OperationError(
                severity="error",
                code="value",
                diagnostics="{}".format(e),
                status_code=404,
            )

    def create(self, Model, resource):
        try:
            new_resource = Model.create_from_resource(resource, query=self.query)
        except Exception as e:
            diag = "{}".format(e)
            if settings.DEBUG:
                import traceback
                tb = traceback.format_exc()
                diag += " {}".format(tb)
            raise OperationError(
                severity="error",
                code="invalid",
                diagnostics="{}".format(diag),
                status_code=422,
            )
        return new_resource


class PutRequestHandler(RequestHandler):
    """
    Receive a request url and the request body of a POST request and handle it. This includes parsing the string into a
    :class:`fhirball.server.requestparser.FhirRequestQuery`, finding the model for the requested
    resource and creating a new instance.
    It returns a tuple (response json, status code).
    If an error occurs during the process, an OperationOutcome is returned.

    :param url: a string containing the path of the request. It should not contain the server
                path. For example: `Patients/123?name:contains=Jo`
    :type url: string
    :param body: a dictionary containing all data that was sent with the request
    :type body: dict

    :returns: A tuple ``(response_json, status code)``, where response_json may be the requested resource,
              a Bundle or an OperationOutcome in case of an error.
    :rtype: tuple

    """
    def handle(self, url, body):
        try:
            self.body = body
            self.parse_url(url)
            # Import the model mappings
            models = self.import_models()
            # Get the Model class
            Model = self.get_resource(models)

            from fhirball.Fhir import resources
            # Get the Resource class
            Resource = self.get_resource(resources)
            # Validate the incoming json and instantiate the Fhir resource
            resource = self.request_body_to_resource(Resource)

            created_resource = self.create(Model, resource)
            return created_resource.to_fhir().as_json(), 201

        except OperationError as e:
            return e.to_fhir().as_json(), e.status_code

    def request_body_to_resource(self, Resource):
        # Validate the incoming json
        try:
            resource = Resource(self.body)
            return resource
        except Exception as e:
            raise OperationError(
                severity="error",
                code="value",
                diagnostics="{}".format(e),
                status_code=404,
            )

    def create(self, Model, resource):
        try:
            new_resource = Model.create_from_resource(resource, query=self.query)
        except Exception as e:
            diag = "{}".format(e)
            if settings.DEBUG:
                import traceback
                tb = traceback.format_exc()
                diag += " {}".format(tb)
            raise OperationError(
                severity="error",
                code="invalid",
                diagnostics="{}".format(diag),
                status_code=422,
            )
        return new_resource
