"""SourceClearCommand is used to clear a or all sources."""

import sys
from logging import getLogger

from requests import codes

from qpc import messages, source
from qpc.clicommand import CliCommand
from qpc.request import DELETE, GET, request
from qpc.translation import _
from qpc.utils import handle_error_response

logger = getLogger(__name__)


class SourceClearCommand(CliCommand):
    """Defines the clear command.

    This command is for clearing a specific source or all source
    sources.
    """

    SUBCOMMAND = source.SUBCOMMAND
    ACTION = source.CLEAR

    def __init__(self, subparsers):
        """Create command."""
        CliCommand.__init__(
            self,
            self.SUBCOMMAND,
            self.ACTION,
            subparsers.add_parser(self.ACTION),
            GET,
            source.SOURCE_URI,
            [codes.ok],
        )
        group = self.parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--name", dest="name", metavar="NAME", help=_(messages.SOURCE_NAME_HELP)
        )
        group.add_argument(
            "--all",
            dest="all",
            action="store_true",
            help=_(messages.SOURCE_CLEAR_ALL_HELP),
        )

    def _build_req_params(self):
        if self.args.name:
            self.req_params = {"name": self.args.name}

    def _delete_entry(self, source_entry, print_out=True):
        deleted = False
        delete_uri = source.SOURCE_URI + str(source_entry["id"]) + "/"
        response = request(DELETE, delete_uri, parser=self.parser)
        name = source_entry["name"]
        if response.status_code == codes.no_content:
            deleted = True
            if print_out:
                logger.info(_(messages.SOURCE_REMOVED), name)
        else:
            handle_error_response(response)
            if print_out:
                logger.error(_(messages.SOURCE_FAILED_TO_REMOVE), name)
        return deleted

    def _handle_response_success(self):
        json_data = self.response.json()
        count = json_data.get("count", 0)
        results = json_data.get("results", [])
        if self.args.name and count == 0:
            logger.error(_(messages.SOURCE_NOT_FOUND), self.args.name)
            sys.exit(1)
        elif self.args.name and count == 1:
            # delete single credential
            entry = results[0]
            if self._delete_entry(entry) is False:
                sys.exit(1)
        elif count == 0:
            logger.error(_(messages.SOURCE_NO_SOURCES_TO_REMOVE))
            sys.exit(1)
        else:
            # remove all entries
            remove_error = []
            next_link = json_data.get("next")
            for entry in results:
                if self._delete_entry(entry, print_out=False) is False:
                    remove_error.append(entry["name"])
            if remove_error:
                cred_err = ",".join(remove_error)
                logger.error(_(messages.SOURCE_PARTIAL_REMOVE), cred_err)
                sys.exit(1)
            elif not next_link:
                logger.info(messages.SOURCE_CLEAR_ALL_SUCCESS)
            else:
                self._do_command()
