from itertools import zip_longest

from jinja2 import FileSystemLoader, TemplateNotFound


def iterable_converged(left, right):
    """
    Returns True, None if the two iterables generate identical, False, index otherwise.
    The index indicates the first position where the iterables differ
    """
    for i, (l_item, r_item) in enumerate(zip_longest(left, right)):
        if l_item != r_item:
            return False, i
    return True, None


class RestrictedFileSystemLoader(FileSystemLoader):
    def get_source(self, environment, template):
        self._ensure_not_unsafe_github(template)
        self._ensure_not_git(template)

        return super().get_source(environment, template)

    def list_templates(self):
        def only_safe(template):
            try:
                self._ensure_not_git(template)
                self._ensure_not_unsafe_github(template)
                return True
            except TemplateNotFound:
                return False

        return filter(only_safe, super().list_templates())

    @staticmethod
    def _ensure_not_unsafe_github(template):
        if template.startswith(".github/") and not (
            template.endswith(".ght") or template.endswith(".j2")
        ):
            raise TemplateNotFound(
                f"Templates under the .github/ folder must end in .ght or j2: {template}"
            )

    @staticmethod
    def _ensure_not_git(template):
        if template.startswith(".git/"):
            raise TemplateNotFound(f"The .git folder is not a valid path for templates: {template}")
