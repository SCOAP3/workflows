import os

from common.constants import (
    ARXIV_EXTRACTION_PATTERN,
    LICENSE_VERSION_PATTERN,
    NODE_ATTRIBUTE_NOT_FOUND_ERRORS,
    REMOVE_SPECIAL_CHARS,
)
from common.parsing.parser import IParser
from common.parsing.xml_extractors import (
    AttributeExtractor,
    CustomExtractor,
    TextExtractor,
)
from common.utils import (
    construct_license,
    extract_text,
    get_license_type,
    get_license_type_and_version_from_url,
    parse_country_from_value,
    parse_to_int,
)
from idutils import is_arxiv
from inspire_utils.date import PartialDate
from structlog import get_logger


class IOPParser(IParser):
    article_type_mapping = {
        "research-article": "article",
        "corrected-article": "article",
        "original-article": "article",
        "correction": "corrigendum",
        "addendum": "addendum",
        "editorial": "editorial",
    }

    def __init__(self, file_path=None):
        self.file_path = file_path
        self.dois = None
        self.year = None
        self.journal_doctype = None
        self.collaborations = []
        self.logger = get_logger().bind(class_name=type(self).__name__)
        extractors = [
            CustomExtractor(
                destination="dois",
                extraction_function=self._get_dois,
                required=True,
            ),
            CustomExtractor(
                destination="journal_doctype",
                extraction_function=self._get_journal_doctype,
            ),
            CustomExtractor(
                destination="related_article_doi",
                extraction_function=self._get_related_article_doi,
            ),
            CustomExtractor(
                destination="arxiv_eprints",
                extraction_function=self._get_extracted_arxiv_eprint_value,
            ),
            AttributeExtractor(
                destination="page_nr",
                source="front/article-meta/counts/page-count",
                attribute="count",
                extra_function=lambda x: [parse_to_int(x)] if parse_to_int(x) else None,
            ),
            CustomExtractor(
                destination="authors",
                extraction_function=self._extract_authors,
                required=True,
            ),
            CustomExtractor(
                destination="date_published",
                extraction_function=self._get_date_published,
            ),
            CustomExtractor(
                destination="journal_year",
                extraction_function=self._get_journal_year,
                required=True,
            ),
            CustomExtractor(
                destination="copyright_year",
                extraction_function=self._extract_copyright_year,
            ),
            CustomExtractor(
                destination="copyright_statement",
                extraction_function=self._extract_copyright_statement,
            ),
            CustomExtractor(
                destination="journal_title",
                extraction_function=self._extract_journal_title,
                required=True,
            ),
            CustomExtractor(
                destination="journal_volume",
                extraction_function=self._extract_journal_volume,
            ),
            CustomExtractor(
                destination="journal_issue",
                extraction_function=self._extract_journal_issue,
            ),
            CustomExtractor(
                destination="journal_artid",
                extraction_function=self._extract_journal_artid,
            ),
            CustomExtractor(
                destination="collaborations",
                extraction_function=self._get_collaborations,
            ),
            TextExtractor(
                destination="title",
                required=True,
                all_content_between_tags=True,
                source="front/article-meta/title-group/article-title",
                remove_tags=True,
            ),
            TextExtractor(
                destination="subtitle",
                required=False,
                source="front/article-meta/subtitle",
            ),
            CustomExtractor(
                destination="license",
                extraction_function=self._get_license,
                required=True,
            ),
            TextExtractor(
                destination="abstract",
                source="front/article-meta/abstract/p",
                all_content_between_tags=True,
                extra_function=lambda x: x,
                remove_tags=True,
            ),
            CustomExtractor(
                destination="files",
                extraction_function=self._get_local_files,
            ),
        ]
        super().__init__(extractors)

    def _get_dois(self, article):
        node = article.find("front/article-meta/article-id/[@pub-id-type='doi']")
        if node is None:
            return
        dois = node.text
        if dois:
            self.logger.msg("Parsing dois for article", dois=dois)
            self.dois = dois
            return [dois]
        return

    def _get_journal_doctype(self, article):
        node = article.find(".")
        value = node.get("article-type")
        if not value:
            self.logger.error("Article-type is not found in XML", dois=self.dois)
            return None
        try:
            self.journal_doctype = self.article_type_mapping[value]
            return self.journal_doctype
        except KeyError:
            self.logger.error(
                "Unmapped article type", dois=self.dois, article_type=value
            )
        except Exception:
            self.logger.error("Unknown error", dois=self.dois)

    def _get_related_article_doi(self, article):
        if self.journal_doctype not in ["corrigendum", "addendum"]:
            return
        node = article.find("front/article-meta/related-article[@ext-link-type='doi']")
        try:
            related_article_doi = node.get("href")
            if related_article_doi:
                self.logger.info("Adding related_article_doi.")
                return [related_article_doi]
        except AttributeError:
            self.logger.error("No related article dois found", dois=self.dois)
            return

    def _get_extracted_arxiv_eprint_value(self, article):
        arxivs_value = article.find(
            "front/article-meta/custom-meta-group/custom-meta/meta-value"
        )
        try:
            arxiv_value = ARXIV_EXTRACTION_PATTERN.sub("", arxivs_value.text.lower())
            if is_arxiv(arxiv_value):
                return [{"value": arxiv_value}]
            self.logger.error("The arXiv value is not valid.", dois=self.dois)
        except AttributeError:
            self.logger.error("No arXiv eprints found", dois=self.dois)

    def _get_date_element(self, article):
        date = (
            article.find("front/article-meta/history/date[@date-type='published']")
            or article.find("front/article-meta/history/date[@date-type='epub']")
            or article.find("front/article-meta/history/pub-date[@pub-type='ppub']")
            or article.find("front/article-meta/pub-date")
        )
        return date

    def _get_date_published(self, article):
        date_element = self._get_date_element(article)
        return self._get_date(date_element)

    def _get_date(self, date):
        try:
            year = int(date.find("year").text)
            self.year = year
        except NODE_ATTRIBUTE_NOT_FOUND_ERRORS:
            self.logger.error("Cannot find year of date_published in XML")
        try:
            month = int(date.find("month").text)
        # was discussed with Anne: if the day is not present, we return year and month
        # if the month value is not present - we return just year
        # if the year is not present - the parsing should crash, because according schema
        # the publication_year is required, which is take from date_published
        except NODE_ATTRIBUTE_NOT_FOUND_ERRORS:
            self.logger.error("Cannot find month of date_published in XML")
            month = None
        try:
            day = int(date.find("day").text)
        except NODE_ATTRIBUTE_NOT_FOUND_ERRORS:
            self.logger.error("Cannot find day of date_published in XML")
            day = None
        try:
            date = PartialDate(year=self.year, month=month, day=day)
            return PartialDate.dumps(date)
        except NODE_ATTRIBUTE_NOT_FOUND_ERRORS + (ValueError,):
            return str(self.year)

    def _get_journal_year(self, article):
        return self.year

    def _extract_authors(self, article):
        contrib_types = article.findall(
            "front/article-meta/contrib-group/contrib[@contrib-type='author']"
        )
        authors = []
        surname = ""
        given_names = ""

        for contrib_type in contrib_types:
            surname = self._extract_surname(contrib_type)
            given_names = self._extract_given_names(contrib_type)
            reffered_ids = contrib_type.findall("xref[@ref-type='aff']")
            affiliations = [
                self._get_affiliation_value(article, reffered_id)
                for reffered_id in reffered_ids
                if self._get_affiliation_value(article, reffered_id)
            ]
            email = self._extract_email(contrib_type)
            author = {}
            if surname:
                author["surname"] = surname
            if given_names:
                author["given_names"] = given_names
            if email:
                author["email"] = email
            if affiliations:
                author["affiliations"] = affiliations
            if author:
                authors.append(author)
        return authors

    def _extract_email(self, contrib_type):
        return extract_text(
            article=contrib_type,
            path="email",
            field_name="email",
            dois=self.dois,
        )

    def _extract_surname(self, contrib_type):
        return extract_text(
            article=contrib_type,
            path="name/surname",
            field_name="surname",
            dois=self.dois,
        )

    def _extract_given_names(self, contrib_type):
        try:
            given_names = contrib_type.find("name/given-names").text
            # IOP puts the collaboration in authors as 'author' with the given_name,
            # which value actually is calloboration name
            if "collaboration" not in given_names.lower():
                return given_names
            else:
                self.collaborations.append(REMOVE_SPECIAL_CHARS.sub("", given_names))
        except AttributeError:
            self.logger.error("Given_names is not found in XML", dois=self.dois)

    def _get_affiliation_value(self, article, reffered_id):
        try:
            institution_and_country = {}
            rid = reffered_id.get("rid")
            institution = self._get_institution(article, rid)
            country = self._get_country(article, rid)
            if country:
                institution_and_country["country"] = country
            if institution:
                institution_and_country["organization"] = institution
                institution_and_country["value"] = institution
                if country:
                    institution_and_country["value"] = ", ".join([institution, country])
            return institution_and_country
        except AttributeError:
            self.logger.error("Referred id is not found")

    def _get_institution(self, article, id):
        return extract_text(
            article=article,
            path=f"front/article-meta/contrib-group/aff[@id='{id}']/institution",
            field_name="institution",
            dois=self.dois,
        )

    def _get_country(self, article, id):
        country = extract_text(
            article=article,
            path=f"front/article-meta/contrib-group/aff[@id='{id}']/country",
            field_name="country",
            dois=self.dois,
        )
        if not country:
            return
        return parse_country_from_value(country)

    def _extract_copyright_year(self, article):
        return extract_text(
            article=article,
            path="front/article-meta/permissions/copyright-year",
            field_name="copyright_year",
            dois=self.dois,
        )

    def _extract_copyright_statement(self, article):
        return extract_text(
            article=article,
            path="front/article-meta/permissions/copyright-statement",
            field_name="copyright_statement",
            dois=self.dois,
        )

    def _extract_journal_title(self, article):
        return extract_text(
            article=article,
            path="front/journal-meta/journal-title-group/journal-title",
            field_name="journal_title",
            dois=self.dois,
        )

    def _extract_journal_volume(self, article):
        return extract_text(
            article=article,
            path="front/article-meta/volume",
            field_name="journal_volume",
            dois=self.dois,
        )

    def _extract_journal_issue(self, article):
        return extract_text(
            article=article,
            path="front/article-meta/issue",
            field_name="journal_issue",
            dois=self.dois,
        )

    def _extract_journal_artid(self, article):
        return extract_text(
            article=article,
            path="front/article-meta/elocation-id",
            field_name="journal_artid",
            dois=self.dois,
        )

    def _get_collaborations(self, article):
        return self.collaborations

    def _get_license_type_and_version(self, license_node, url):
        try:
            license_type = license_node.get("license-type")
            version = LICENSE_VERSION_PATTERN.search(url).group(0)
            return construct_license(
                license_type=license_type.upper(), version=version, url=url
            )
        except AttributeError:
            return

    def _get_license_from_text(self, license_node):
        license_text = extract_text(
            path="license-p/ext-link",
            article=license_node,
            field_name="ext-link",
            dois=self.dois,
        )
        license_type = get_license_type(license_text=license_text)
        version = LICENSE_VERSION_PATTERN.search(license_text).group(0)
        return construct_license(license_type=license_type, version=version)

    def _get_license(self, article):
        licenses = []
        licenses_nodes = article.findall("front/article-meta/permissions/license")
        for license_node in licenses_nodes:
            try:
                url = license_node.attrib["{http://www.w3.org/1999/xlink}href"]
                type_and_version = get_license_type_and_version_from_url(url=url)
                if type_and_version:
                    licenses.append(type_and_version)
            except KeyError:
                self.logger.error("License is not found in XML.")
        return licenses

    def _get_local_files(self, article):
        if not self.file_path:
            self.logger.error("No file path provided")
            return
        self.logger.msg("Parsing local files", file=self.file_path)

        dir_path = os.path.dirname(self.file_path)
        file_name = os.path.basename(self.file_path).split(".")[0]
        pdf_path = os.path.join(dir_path, f"{file_name}.pdf")

        files = {
            "xml": self.file_path,
            "pdf": pdf_path,
        }
        self.logger.msg("Local files parsed", files=files)
        return files
