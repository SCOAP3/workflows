from os import getenv

from common.request import Request


class APSApiClient:
    def __init__(
        self,
        base_url=None,
        path_segments=None,
    ):
        self.base_url = base_url or getenv("APS_API_BASE_URL", "http://harvest.aps.org")
        self.path_segments = path_segments or ["v2", "journals", "articles"]

    def get_articles_metadata(self, parameters=None, doi=None):
        all_path_segments = self.path_segments
        if doi is not None:
            all_path_segments = self.path_segments + [doi]
        request = Request(
            base_url=self.base_url,
            path_segments=all_path_segments,
            parameters=parameters,
        )
        response_content = request.get_response_json()
        data = response_content.get("data")
        if isinstance(data, dict):
            # Single DOI
            return {"data": [data]}
        if data:
            return response_content

    def get_pdf_file(self, doi):
        all_path_segments = self.path_segments + [doi]
        headers = {"Accept": "application/pdf"}
        request = Request(
            base_url=self.base_url,
            path_segments=all_path_segments,
            headers=headers,
        )
        response_content = request.get_response_bytes()
        return response_content

    def get_xml_file(self, doi):
        all_path_segments = self.path_segments + [doi]
        headers = {"Accept": "text/xml"}
        request = Request(
            base_url=self.base_url,
            path_segments=all_path_segments,
            headers=headers,
        )
        response_content = request.get_response_bytes()
        return response_content

    def __repr__(self):
        return f"<APSApiClient base_url={self.base_url}, \
                    path_segments={self.path_segments}, \
                    parameters={self.parameters}>"
