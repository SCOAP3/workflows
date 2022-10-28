import datetime
import re
import xml.etree.ElementTree as ET

from common.parsing.parser import IParser
from common.parsing.xml_extractors import AttributeExtractor, CustomExtractor
from hindawi.xml_extractors import HindawiTextExtractor as TextExtractor
from structlog import get_logger

# FIXME used Hindawi xml extractor, because it has mathlib string handling


class IOPParser(IParser):
    def __init__(self) -> None:
        self.logger = get_logger().bind(class_name=type(self).__name__)
        self.article_type_mapping = {
            "research-article": "article",
            "corrected-article": "article",
            "original-article": "article",
            "correction": "corrigendum",
            "addendum": "addendum",
            "editorial": "editorial",
        }
        extractors = [
            TextExtractor(
                destination="dois",
                source="front/article-meta/article-id/[@pub-id-type='doi']",
                extra_function=lambda x: [x],
                default_value=[],
            ),
            CustomExtractor(
                destination="journal_doctype",
                extraction_function=self._get_journal_doctype,
                default_value="",
            ),
            CustomExtractor(
                destination="related_article_doi",
                extraction_function=self._get_related_article_doi,
                default_value=[],
            ),
            CustomExtractor(
                destination="arxiv_eprints",
                extraction_function=self._get_arxiv_eprints,
                default_value=[],
            ),
            AttributeExtractor(
                destination="page_nr",
                source="front/article-meta/counts/page-count",
                attribute="count",
                extra_function=lambda x: [int(x)],
                default_value=[0],
            ),
            TextExtractor(
                destination="abstract",
                source="front/article-meta/abstract/p",
                extra_function=lambda x: x,
                default_value="",
            ),
            TextExtractor(
                destination="title",
                source="front/article-meta/title-group/article-title",
                extra_function=lambda x: " ".join(x.split()),
                default_value="",
            ),
            TextExtractor(
                destination="subtitle",
                required=False,
                source="front/article-meta/subtitle",
                extra_function=lambda x: " ".join(x.split()),
                default_value="",
            ),
            CustomExtractor(
                destination="authors",
                extraction_function=self._get_affiliations,
                default_value=[],
            ),
            CustomExtractor(
                destination="date_published",
                extraction_function=self._get_date_published,
                default_value="2000-00-00",
            ),
            CustomExtractor(
                destination="publication_info",
                extraction_function=self._get_publication_info,
                required=True,
                default_value=[],
            ),
            CustomExtractor(
                destination="date_published",
                extraction_function=self._get_date_published,
                default_value="2000-00-00",
            ),
            TextExtractor(
                destination="copyright_holder",
                source="front/article-meta/permissions/copyright-holder",
                required=False,  # copyright is required
                extra_function=lambda x: x,
                default_value="",
            ),
            TextExtractor(
                destination="copyright_year",
                source="front/article-meta/permissions/copyright-year",
                extra_function=lambda x: x,
                default_value=0,
            ),
            TextExtractor(
                destination="copyright_statement",
                source="front/article-meta/permissions/copyright-statement",
                extra_function=lambda x: x,
                default_value="",
            ),
            CustomExtractor(
                destination="license",
                extraction_function=self._get_license,
                required=True,
                default_value=[],
            ),
        ]
        super().__init__(extractors)

    def _get_journal_doctype(self, article: ET.Element):
        raw_journal_doctype = article.find(
            ".",
        ).get("article-type")
        journal_doctype = self.article_type_mapping[raw_journal_doctype]
        if "other" in journal_doctype:
            doi = article.find("front/article-meta/article-id/[@pub-id-type='doi']")
            self.logger.msg(
                f"There are unmapped article types for article {doi} with types {raw_journal_doctype}"
            )
        return journal_doctype

    def _get_related_article_doi(self, article):
        journal_doctype = self._get_journal_doctype(article)
        if journal_doctype in ["correction", "addendum"]:
            self.logger.msg("Adding related_article_doi.")
            return article.find("./related-article[@ext-link-type='doi']/@href")

    def _get_arxiv_eprints(self, article):
        arxiv_eprints = []
        arxivs_value = article.find(
            "front/article-meta/custom-meta-group/custom-meta/meta-value"
        ).text.lower()
        pattern = re.compile(r"(arxiv:|v[0-9]$)", flags=re.I)
        arxiv_eprints.append({"value": pattern.sub("", arxivs_value)})
        return arxiv_eprints

    def _get_institutions(self, article, reffered_id):
        return article.findall(
            f"front/article-meta/contrib-group/aff[@id='{reffered_id.get('rid')}']/institution"
        )

    def _get_countries(self, article, reffered_id):
        return article.findall(
            f"front/article-meta/contrib-group/aff[@id='{reffered_id.get('rid')}']/country"
        )

    def _get_affiliation_values(self, institutions, countries):
        return [
            {
                "value": ",".join([institution.text, country.text]),
                "country": country.text,
            }
            for institution, country in zip(institutions, countries)
        ]

    def _get_affiliations(self, article):
        contrib_types = article.findall(
            "front/article-meta/contrib-group/contrib[@contrib-type='author']"
        )
        authors = []
        for contrib_type in contrib_types:
            surname = contrib_type.find("name/surname").text
            given_names = contrib_type.find("name/given-names").text
            reffered_id = contrib_type.find("xref[@ref-type='aff']")
            if reffered_id is None:
                continue
            institutions = self._get_institutions(article, reffered_id)
            countries = self._get_countries(article, reffered_id)
            affiliations = self._get_affiliation_values(institutions, countries)
            author = {
                "surname": surname,
                "given_names": given_names,
                "affiliations": affiliations,
            }
            authors.append(author)
        return authors

    def _get_date(self, date):
        return datetime.date(
            day=int(date.find("day").text),
            month=int(date.find("month").text),
            year=int(date.find("year").text),
        ).isoformat()

    def _get_date_published(self, article):
        date = (
            article.find("front/article-meta/history/date[@date-type='published']")
            or article.find("front/article-meta/history/date[@date-type='epub']")
            or article.find("front/article-meta/history/pub-date[@pub-type='ppub']")
            or article.find("front/article-meta/pub-date")
        )
        if date:
            return self._get_date(date)
        return datetime.date.today().isoformat()

    def _get_journal_year(self, article):
        date = self._get_date_published(article)
        dt = datetime.datetime.strptime(date, "%Y-%m-%d")
        return dt.year

    def _construct_license(self, url, license_type, version):
        if url and license_type and version:
            return {
                "url": url,
                "license": f"CC-{license_type}-{version}",
            }

    def _get_license(self, article: ET.Element):
        licenses = []
        license_texts = article.findall(
            "front/article-meta/permissions/license/license-p/ext-link"
        )
        urls = article.findall("front/article-meta/permissions/license")
        license_urls = [
            url.attrib["{http://www.w3.org/1999/xlink}href"] for url in urls
        ]
        for license_url, license_text in zip(license_urls, license_texts):
            if license_url:
                url_parts = license_url.split("/")
                clean_url_parts = list(filter(bool, url_parts))
                version = clean_url_parts.pop()
                license_type = clean_url_parts.pop()
                licenses.append(
                    self._construct_license(license_url, license_type.upper(), version)
                )
            elif license_text.text:
                licenses.append(license_text.text)
        return licenses

    def _get_publication_info(self, article):
        return [
            {
                "journal_title": article.find(
                    "front/journal-meta/journal-title-group/journal-title",
                ).text,
                "journal_volume": article.find(
                    "front/article-meta/volume",
                ).text,
                "journal_year": self._get_journal_year(article),
                "journal_issue": article.find("front/article-meta/issue").text,
                "journal_artid": article.find("front/article-meta/elocation-id").text,
            }
        ]
