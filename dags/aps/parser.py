import logging
import re

from common.parsing.json_extractors import CustomExtractor, NestedValueExtractor
from common.parsing.parser import IParser
from common.parsing.xml_extractors import CustomExtractor as XMLCustomExtractor
from common.utils import construct_license
from inspire_utils.record import get_value

logger = logging.getLogger("airflow.task")


class APSParser(IParser):
    def __init__(self) -> None:
        article_type_mapping = {
            "article": "article",
            "erratum": "erratum",
            "editorial": "editorial",
            "retraction": "retraction",
            "essay": "other",
            "comment": "other",
            "letter-to-editor": "other",
            "rapid": "other",
            "brief": "other",
            "reply": "other",
            "announcement": "other",
            "nobel": "other",
        }

        extractors = [
            NestedValueExtractor(
                "dois", json_path="identifiers.doi", extra_function=lambda x: [x]
            ),
            NestedValueExtractor(
                "journal_doctype",
                json_path="articleType",
                extra_function=lambda x: article_type_mapping.get(x, "other"),
            ),
            NestedValueExtractor(
                "page_nr", json_path="numPages", extra_function=lambda x: [x]
            ),
            NestedValueExtractor(
                "arxiv_eprints",
                json_path="identifiers.arxiv",
                extra_function=lambda x: [
                    {"value": re.sub("arxiv:", "", x, flags=re.IGNORECASE)}
                ],
            ),
            NestedValueExtractor("abstract", json_path="abstract.value"),
            NestedValueExtractor("title", json_path="title.value"),
            CustomExtractor("authors", self._form_authors),
            NestedValueExtractor("journal_title", json_path="journal.name"),
            NestedValueExtractor("journal_issue", json_path="issue.number"),
            NestedValueExtractor("journal_volume", json_path="volume.number"),
            NestedValueExtractor(
                "journal_year",
                json_path="date",
                extra_function=lambda x: int(x[:4] if (len(x) >= 4) else 0000),
            ),
            NestedValueExtractor("date_published", json_path="date"),
            NestedValueExtractor(
                "copyright_holder",
                json_path="rights.copyrightHolders",
                extra_function=lambda x: x[0]["name"] if len(x) >= 1 else "",
            ),
            NestedValueExtractor("copyright_year", json_path="rights.copyrightYear"),
            NestedValueExtractor(
                "copyright_statement", json_path="rights.rightsStatement"
            ),
            CustomExtractor(
                "license",
                extraction_function=lambda x: self._get_licenses(x),
            ),
            CustomExtractor(
                "collections",
                extraction_function=lambda x: ["HEP", "Citeable", "Published"],
            ),
            CustomExtractor("field_categories", self._get_field_categories),
        ]

        super().__init__(extractors)

    def _form_authors(self, article):
        authors = article["authors"]
        return [
            {
                "full_name": author["name"],
                "given_names": author["firstname"],
                "surname": author["surname"],
                "affiliations": self._get_affiliations(
                    article, set(author["affiliationIds"])
                )
                if "affiliationIds" in author
                else [],
            }
            for author in authors
            if author["type"] == "Person"
        ]

    def extract_organization_and_ror(self, text):
        pattern = r'<a href="([^"]+)">(.*?)</a>.*'

        ror_url = None

        def replace_and_capture(match):
            nonlocal ror_url
            ror_url = match.group(1)
            return match.group(2)

        modified_text = re.sub(pattern, replace_and_capture, text)

        return modified_text, ror_url

    def _get_affiliations(self, article, affiliationIds):
        parsed_affiliations = []
        for affiliation in article["affiliations"]:
            if affiliation.get("id") in affiliationIds:
                org_name, ror = self.extract_organization_and_ror(affiliation["name"])

                parsed_affiliations.append(
                    {
                        "value": affiliation[
                            "name"
                        ],  
                        "organization": org_name,  
                        "ror": ror,  
                    }
                )
        return parsed_affiliations

    def _get_field_categories(self, article):
        return [
            {
                "term": term.get("label"),
                "scheme": "APS",
                "source": "",
            }
            for term in get_value(
                article, "classificationSchemes.subjectAreas", default=""
            )
        ]

    def _get_licenses(self, x):
        try:
            rights = x["rights"]["licenses"]
            licenses = []
            for right in rights:
                url = right["url"]
                url_parts = url.split("/")
                if url == "http://link.aps.org/licenses/aps-default-license":
                    license_type = "CC-BY"
                    version = "3.0"
                else:
                    clean_url_parts = list(filter(bool, url_parts))
                    version = clean_url_parts.pop()
                    license_type = f"CC-{clean_url_parts.pop()}"
                licenses.append(
                    construct_license(
                        url=url, license_type=license_type.upper(), version=version
                    )
                )
            return licenses
        except Exception:
            logger.error("Error was raised while parsing licenses.")


class APSXMLParser(IParser):
    def __init__(self):
        extractors = [
            XMLCustomExtractor("authors", self._get_authors),
            XMLCustomExtractor("data_availability", self._get_data_availability),
        ]
        super().__init__(extractors)

    def _get_affiliations(self, article, contrib):
        affiliations = []

        xref_elements = contrib.findall(".//xref[@ref-type='aff']")

        if not xref_elements:
            logger.info("No affiliations found for this author.")
            return affiliations

        for xref in xref_elements:
            ref_ids = list(xref.get("rid").split(" "))
            for ref_id in ref_ids:
                affiliation_node = article.find(f".//aff[@id='{ref_id}']")

                if affiliation_node is not None:
                    full_text_parts = []
                    ror = None

                    for child in affiliation_node.iter():
                        if (
                            child.tag == "institution-id"
                            and child.get("institution-id-type") == "ror"
                        ):
                            ror = child.text
                        elif (
                            child.tag not in ["label", "sup", "institution-id"]
                            and child.text
                        ):
                            full_text_parts.append(child.text.strip())
                        if child.tail:
                            full_text_parts.append(child.tail.strip())

                    raw_aff_text = " ".join(filter(None, full_text_parts))
                    aff_text = re.sub(r"\s*,\s*,*", ", ", raw_aff_text)
                    aff_text = re.sub(r"\s+", " ", aff_text).strip()

                    affiliations.append({"value": aff_text, "ror": ror})
                else:
                    logger.info(f"Affiliation with id '{ref_id}' not found.")

        return affiliations

    def _get_authors(self, article):
        authors = []

        contrib_groups = article.findall("./front/article-meta/contrib-group")
        if not contrib_groups:
            return authors

        for contrib_group in contrib_groups:
            for contrib in contrib_group.findall("./contrib[@contrib-type='author']"):
                author = {}

                name = contrib.find("./name")
                if name is not None:
                    given_names = name.find("given-names")
                    surname = name.find("surname")
                    author["given_names"] = (
                        given_names.text if given_names is not None else ""
                    )
                    author["surname"] = surname.text if surname is not None else ""
                    author["full_name"] = (
                        f"{author['given_names']} {author['surname']}".strip()
                    )

                orcid = contrib.find("./contrib-id[@contrib-id-type='orcid']")
                if orcid is not None:
                    author["orcid"] = orcid.text.strip() if orcid.text else None

                authors.append(author)

        return authors

    def _get_data_availability(self, article):
        data_availability_sec = article.find(".//sec[@sec-type='data-availability']")
        if data_availability_sec is None:
            return None

        result = {"statement": None, "urls": None}

        statement_parts = []
        for p in data_availability_sec.findall(".//p"):
            if p.text:
                statement_parts.append(p.text.strip())
            for elem in p:
                if elem.tail:
                    statement_parts.append(elem.tail.strip())
        statement = " ".join(filter(None, statement_parts))

        urls = []
        xref_elements = data_availability_sec.findall(".//xref[@ref-type='bibr']")

        for xref in xref_elements:
            rid_value = xref.get("rid")
            if not rid_value:
                continue
            ref_ids = rid_value.split(" ")
            for ref_id in ref_ids:
                ref_element = article.find(f".//ref[@id='{ref_id}']")
                if ref_element is not None:
                    for pub_id in ref_element.findall(".//pub-id"):
                        if pub_id.text:
                            urls.append(pub_id.text.strip())

        if statement:
            result["statement"] = statement
        if urls:
            result["urls"] = urls

        return result if any(result.values()) else None
