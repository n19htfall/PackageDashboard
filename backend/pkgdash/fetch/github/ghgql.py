import logging
import time
from typing import Dict, Iterable, List, Tuple, Callable, Any, Literal
from datetime import datetime, timedelta
from beanie import BulkWriter
from dateutil.parser import parse as parse_date

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
from gql.transport.exceptions import TransportQueryError, TransportServerError

# make requests logger less verbose
from gql.transport.requests import log as requests_logger
from pydantic import ValidationError
requests_logger.setLevel(logging.WARNING)

# global utc
from pytz import timezone

TZ_UTC = timezone("UTC")


class GitHubGraphQLClient(object):
    @staticmethod
    def _load_graphql_schema(schema_path: str) -> str or None:
        schema_url = "https://docs.github.com/public/schema.docs.graphql"
        try:
            with open(schema_path, "r") as f:
                return f.read()
        except FileNotFoundError:
            logging.info("Could not load schema: %s, getting from GitHub", schema_path)
            try:
                # load the graphql schema
                import requests
                r = requests.get(schema_url)
                if r.status_code == 200:
                    with open(schema_path, "w", encoding="utf-8") as f:
                        f.write(r.text)
                    return r.text
                else:
                    raise Exception(
                        "Could not load schema from GitHub: HTTP %s" % r.status_code
                    )
            except Exception as e:
                logging.error("Could not load schema from GitHub: %s", e)
                return None

    def __init__(
        self,
        github_token: str or Iterable[str],
        num_retries: int = 3,
        retry_interval: int = 60,
    ) -> None:
        super().__init__()

        self._logger = logging.getLogger(__name__)
        self._token = github_token
        self._token_idx = 0
        self._num_retries = num_retries

        self._schema = None

        # try:
        #     self._schema = self._load_graphql_schema(
        #         CONFIG["gfibot"]["github_graphql_schema_path"]
        #     )
        # except KeyError as e:
        #     self._logger.error("Schema path not found in config: %s", e)
        # if not self._schema:
        #     self._logger.info("Fallback to introspection")

        self._client = self._create_client(
            github_token=self._token, num_retries=self._num_retries, schema=self._schema
        )

        self._retry_interval = retry_interval
        self._reset_at = time.time() + self._retry_interval

    @staticmethod
    def _create_client(github_token: str, num_retries: int = 3, schema = None) -> Client:
        return Client(
            transport=RequestsHTTPTransport(
                url="https://api.github.com/graphql",
                headers={"Authorization": "Bearer {}".format(github_token)},
                verify=True,
                retries=num_retries,
            ),
            fetch_schema_from_transport=(schema is None),
            schema=schema,
        )

    def get_one(self, query: str, variables=None, default=None) -> dict or None:
        retries = 1
        while retries <= self._num_retries:
            try:
                result = self._client.execute(gql(query), variable_values=variables)

                # update reset_at
                reset_at: str or None = result.get("rateLimit", {}).get("resetAt")
                if reset_at:
                    self._reset_at = datetime.strptime(
                        reset_at, "%Y-%m-%dT%H:%M:%SZ"
                    ).timestamp()
                else:
                    self._reset_at = time.time() + self._retry_interval

                return result

            # we got an error from GitHub API
            except TransportQueryError as e:
                # hit rate limit
                # if e.data and e.data.get("type") == "RATE_LIMITED":
                if "RATE_LIMITED" in str(e):
                    if self._token_idx + 1 >= len(self._tokens):
                        # We got nothing to do, just sleep
                        self._token_idx = 0
                        sleep_time = max(self._reset_at - time.time() + 1, 1)
                        self._logger.warning(
                            "Hit rate limit. Sleeping for %d seconds",
                            sleep_time,
                        )
                        time.sleep(sleep_time)
                        self._reset_at = max(
                            self._reset_at, time.time() + self._retry_interval
                        )
                        continue
                    else:
                        # try next token
                        self._token_idx += 1
                        self._logger.warning(
                            "Hit rate limit. Trying next token: %s",
                            "*" * (len(self._tokens[self._token_idx]) - 5)
                            + self._tokens[self._token_idx][-5:],
                        )
                        self._client = self._create_client(
                            github_token=self._tokens[self._token_idx],
                            num_retries=self._num_retries,
                            schema=self._schema,
                        )

                # unknown error
                else:
                    self._logger.error(
                        "GitHub API error: %s, variables: %s", e, variables
                    )
                    break

            # token invalid
            except TransportServerError as e:
                if e.code == 401:
                    self._logger.error(
                        "Unauthenticated: Invalid token %s: %s",
                        "*" * (len(self._token) - 5) + self._token[-5:],
                        e,
                    )
                    break
                else:
                    self._logger.error("Unexpected HTTP %d error: %s", e.code, e)

        return default


class GraphQLQueryComponent(object):
    @staticmethod
    def _wrap_str(s: str or Dict) -> str:
        """Wraps s in quotes if s is not a number, type or variable"""
        # not a str?
        if isinstance(s, dict):
            # don't wrap enums
            return (
                "{"
                + ", ".join(
                    [f"{k}: {GraphQLQueryComponent._wrap_str(v)}" for k, v in s.items()]
                )
                + "}"
            )
        elif not isinstance(s, str):
            s = str(s)
        # is a number?
        if s.isdigit():
            return s
        # is a variable?
        if s[0] == "$":
            return s
        # is a type?
        if s[0].isupper and s.endswith("!"):
            return s
        # is it a enum?
        if s in [
            "ASC",
            "DESC",
            "CREATED_AT",
            "UPDATED_AT",
            "PUSHED_AT",
            "MERGED_AT",
            "CLOSED_AT",
            "FIRST_SEEN_AT",
            "LAST_SEEN_AT",
            "REPOSITORY", 
            "USER",
            "DISCUSSION",
        ]:
            return s
        return '"' + s + '"'

    @staticmethod
    def _add_indent(s: str) -> str:
        """Adds indent to s"""
        return "\n".join(["  " + x for x in s.split("\n")])

    @staticmethod
    def _format_child(s: str or "GraphQLQueryComponent", indent: bool) -> str:
        """Formats a child"""
        if indent:
            if isinstance(s, GraphQLQueryComponent):
                return s.gen_query(indent=True)
            return s
        else:
            if isinstance(s, GraphQLQueryComponent):
                return s.gen_query(indent=False)
            return " ".join(s.replace("\n", "").split())

    def __init__(
        self,
        name: str,
        args: Dict[str, Any] = None,
        callback: Callable[[Dict[str, Any]], None] or None = None,
        *children: "GraphQLQueryComponent" or str,
    ):
        """
        Initializes a GraphQL query component
        :param name: The name of the query component
        :param args: The arguments of the query component
        :param callback: The callback function to be called on query results (optional)
        :param children: The children of the query component (can be strings or GraphQLQueryComponents)

        >>> q = GraphQLQueryComponent("query", {"first": 10}, None, "user", "repository")
        >>> q.gen_query()
        'query(first: 10) {user {repository}} '
        """
        self.name = name
        self.args = args if args else {}

        self._callback = callback
        self.children = children
        self.finished = False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name}, {self.args})"

    def __str__(self):
        """Pretty print attributes"""
        return self.gen_query(indent=False)

    def _init_state(self) -> None:
        """Initializes state"""
        self.finished = False

    def _next_state(self, res: Dict[str, Any]) -> None:
        """Updates state"""
        self.finished = True

    def _propagate_state(self) -> None:
        """Propagates finished attribute to children"""
        # print("propagate_state", str(self))
        if self.finished:
            self._init_state()
        for c in self.children:
            if not isinstance(c, GraphQLQueryComponent):
                continue
            c._propagate_state()

    def update_state(self, res: Dict[str, Any]) -> None:
        """Updates finished attribute"""
        try:
            # print("update_state", str(self))
            # run callback
            if self._callback:
                self._callback(res)

            # update children's state
            self.finished = True
            for c in self.children:
                if not isinstance(c, GraphQLQueryComponent):
                    continue
                # update EVERY child's state and run callback
                if not c.finished:
                    try:
                        c.update_state(res[c.name])
                    except KeyError as e:
                        logging.error(
                            f"{str(self)}: Expecting {c.name} in {res.keys()}"
                        )
                        raise e
                if not c.finished:
                    self.finished = False

            # update self's state if all children have finished
            if self.finished:
                self._next_state(res)

                # has next state
                if not self.finished:
                    # propagate next state to children
                    for c in self.children:
                        if not isinstance(c, GraphQLQueryComponent):
                            continue
                        c._propagate_state()
        except Exception as e:
            logging.error(f"Error executing callback: {str(self)}")
            raise e

    def gen_query(self, indent: bool = True) -> str:
        """
        Generates the query string
        :param indent: The indent level
        :return: The query string
        """
        if self.finished:
            return ""

        q = self.name
        if self.args:
            q += (
                "("
                + ", ".join([f"{k}: {self._wrap_str(v)}" for k, v in self.args.items()])
                + ")"
            )

        if self.children:
            if indent:
                q += "{\n"
                q += "\n".join(
                    [
                        self._add_indent(self._format_child(c, True))
                        for c in self.children
                    ]
                )
                q += "\n}"
            else:
                q += (
                    " {"
                    + " ".join([self._format_child(c, False) for c in self.children])
                    + "}"
                )
        return q


class GraphQLQueryPagedComponent(GraphQLQueryComponent):
    def __init__(
        self,
        name: str,
        args: Dict[str, Any] = None,
        callback: Callable[[Dict[str, Any]], None] or None = None,
        *children: "GraphQLQueryComponent" or str,
    ):
        """
        Initializes a GraphQL query component with pagination
        :param name: The name of the query component
        :param args: The arguments of the query component
        :param callback: The callback function to be called on query results (optional)
        :param children: The children of the query component (can be strings or GraphQLQueryComponents)

        >>> q = GraphQLQueryPagedComponent("query", {"first": 10}, None, "user", "repository")
        >>> q.gen_query()
        'query(first: 10) {user {repository} pageInfo { hasNextPage  endCursor}}'
        """
        super().__init__(name, args, callback, *children)
        self.children = (*self.children, "pageInfo {\n  hasNextPage\n  endCursor\n}")

    def _init_state(self) -> None:
        """Initializes state"""
        self.finished = False
        if "after" in self.args:
            del self.args["after"]

    def _next_state(self, res: Dict[str, Any]) -> None:
        """Updates state"""
        self.finished = not res["pageInfo"]["hasNextPage"]
        if not self.finished:
            self.args["after"] = res["pageInfo"]["endCursor"]


class GraphQLQueryDateComponent(GraphQLQueryComponent):
    @staticmethod
    def _parse_date_utc(s: str) -> datetime:
        return parse_date(s).replace(tzinfo=TZ_UTC)

    def __init__(
        self,
        name: str,
        args: Dict[str, Any] = None,
        callback: Callable[[Dict[str, Any]], None] or None = None,
        *children: "GraphQLQueryComponent" or str,
    ):
        """
        Initializes a GraphQL query component with date range
        :param name: The name of the query component
        :param args: The arguments of the query component ('from' is required, 'to' and 'interval_days' are optional)
        :param callback: The callback function to be called on query results (optional)
        :param children: The children of the query component (can be strings or GraphQLQueryComponents)

        >>> GraphQLQueryDateComponent("query", {"from": "2019-01-01", "to": "2022-01-01", "interval_days": 1}, None, "user", "repository").gen_query()
        'query(from: "2019-01-01T00:00:00Z", to: "2019-01-02T00:00:00Z") {user {repository} startedAt endedAt } '
        >>> GraphQLQueryDateComponent("query", {"from": "2019-01-01T00:00:00Z"}, None, "user", "repository").gen_query()
        'query(from: "2019-01-01T00:00:00Z") {user {repository} startedAt endedAt } '
        >>> GraphQLQueryDateComponent("query", {"from": "2019-01-01", "to": "2019-12-31", "interval_days": 400}, None, "user", "repository").gen_query()
        'query(from: "2019-01-01T00:00:00Z", to: "2019-12-31T00:00:00Z") {user {repository} startedAt endedAt } '
        """
        super().__init__(name, args, callback, *children)
        self.children = (*self.children, "startedAt", "endedAt")

        # read from args: 'from' 'to' 'interval'
        # from is required
        self._from_time = self._parse_date_utc(args["from"])
        # to and interval can be infered
        # fix precision
        self._to_time = (
            self._parse_date_utc(args["to"])
            if "to" in args
            else datetime.now().replace(tzinfo=datetime.utcnow().tzinfo, microsecond=0)
        )
        # print(f"{self}: from {self._from_time} to {self._to_time}", file=sys.stderr)
        self._interval = (
            timedelta(days=args["interval_days"]) if "interval_days" in args else None
        )

        # process args
        self.args["from"] = self._from_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        if "interval_days" in self.args:
            del self.args["interval_days"]

        if not self._interval and "to" in self.args:
            del self.args["to"]

        self._init_state()

    def _init_state(self) -> None:
        """Initializes state"""
        self.finished = False
        self.args["from"] = self._from_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        if self._interval and self._from_time + self._interval < self._to_time:
            self.args["to"] = (self._from_time + self._interval).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

    def _next_state(self, res: Dict[str, Any]) -> None:
        self.finished = self._parse_date_utc(res["endedAt"]) >= self._to_time
        if not self.finished:
            self.args["from"] = res["endedAt"]
            if not self._interval:
                self._interval = self._parse_date_utc(
                    res["endedAt"]
                ) - self._parse_date_utc(res["startedAt"])
            # graphql time
            self.args["to"] = min(
                self._parse_date_utc(res["endedAt"]) + self._interval, self._to_time
            ).strftime("%Y-%m-%dT%H:%M:%SZ")


class GHSearchCollector:
    def __init__(
        self,
        token: str,
        per_page = 100,
    ) -> None:
        self.gh_gql = GitHubGraphQLClient(token)
        self.per_page = per_page

        self._logger = logging.getLogger(__name__)
        self._max_time = None
        self._record_num = -1

    def _handle_callback(self, name: str):
        return self._callbacks[name] if name in self._callbacks else None
    
    def _fetch(self, q: GraphQLQueryComponent) -> None:
        while not q.finished:
            s = q.gen_query(False)
            self._logger.debug(f"Running query: {s}")
            r = self.gh_gql.get_one(q.gen_query(False))
            if r is None:
                self._logger.error("Exception while running query")
                raise Exception("Exception while running query")
            self._logger.debug(f"Got response: rateLimit {r['rateLimit']}")
            try:
                q.update_state(r)
            except Exception as e:
                self._logger.error(f"Exception while updating state: {e}")
                self._logger.error(f"Response: {r}")
                raise e

    @staticmethod
    def _flatten_repo(repo: dict) -> dict:
        _repo_flat = { **repo }
        _repo_flat['licenseInfo'] = repo['licenseInfo']['name'] if repo['licenseInfo'] else None
        _repo_flat['primaryLanguage'] = repo['primaryLanguage']['name'] if repo['primaryLanguage'] else None
        _repo_flat['repositoryTopics'] = [x['topic']['name'] for x in repo['repositoryTopics']['nodes']] if repo['repositoryTopics'] else []
        _repo_flat['description'] = repo['description']
        return _repo_flat
    
    def _handle_repo(self, d: dict[str, str | int], cb: Callable[[dict[str, str | int]], None] or None) -> None:
        r = d['nodes']
        self._record_num = len(r)
        for repo in r:
            _repo_flat = self._flatten_repo(repo)
            if self._max_time is None or self._max_time < parse_date(_repo_flat['pushedAt']):
                self._max_time = _repo_flat['pushedAt']
            if cb is not None:
                cb(_repo_flat)
    
    @staticmethod
    def date_to_str(d: datetime) -> str:
        return d.replace(tzinfo=TZ_UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    def search_repos(self, query: str, pushed_since: datetime = datetime(year=2008, month=1, day=1), callback: Callable[[dict[str, str|int]], None] or None = None) -> None:
        # check the query, no "sort" or "pushed" allowed
        if not query:
            raise ValueError("Query cannot be empty. Use REST API instead if you want to get all repos.")
        
        if "sort:" in query or "pushed:" in query:
            raise ValueError("Query cannot contain 'sort' or 'pushed'. They are reserved for pagination.")

        self._max_time = pushed_since

        while pushed_since <= datetime.now():  # which will never happen
            _pushed_from = self.date_to_str(self._max_time)
            q = GraphQLQueryComponent(
                "query",
                {},
                None,
                "rateLimit {\n  cost\n  limit\n  remaining\n  resetAt\n}",
                GraphQLQueryPagedComponent(
                    "search",
                    {"query": f'\\"{query}\\" sort:updated-asc pushed:>{_pushed_from}', "type": "REPOSITORY", "first": self.per_page},
                    lambda x: self._handle_repo(x, callback),
                    "nodes {\n  ... on Repository {\n    nameWithOwner\n    stargazerCount\n   forkCount\n   createdAt\n    updatedAt\n    pushedAt\n     description\n   isArchived\n    isFork\n    archivedAt\n    isTemplate\n    licenseInfo {\n      name\n    }\n    primaryLanguage {\n      name\n    }\n    repositoryTopics(first: 100) {\n      nodes {\n        topic {\n          name\n        }\n      }\n    }\n  }\n}",
                )
            )
            self._fetch(q)
            self._logger.info(f"Searched repos with query: {q}, pushed_since: {pushed_since}, max_time: {self._max_time}, record_num: {self._record_num}")

            # check the number of records we got
            if self._record_num == 0:
                # seems like we have reached the end
                break



            
if __name__ == "__main__":
    from pkgdash.models.database.repository import RepositoryStats, Repository
    from pkgdash.models.connector.mongo import create_engine
    import asyncio
    from pydantic import BaseModel
    from pkgdash import logger

    client = GitHubGraphQLClient("eb9bbcb46d0ef0537d8ab8c926095766388d7380")

    res = []

    def flatten_output(d: dict) -> list[dict]:
        # print(d)
        repo = d
        _repo_flat = {}
        _repo_flat['url'] = repo['nameWithOwner']
        _repo_flat['n_stars'] = repo['stargazerCount']
        _repo_flat['created_at'] = repo['createdAt']
        _repo_flat['updated_at'] = repo['updatedAt']
        _repo_flat['pushed_at'] = repo['pushedAt']
        _repo_flat['is_fork'] = repo['isFork']
        _repo_flat['archived_at'] = repo['archivedAt']
        _repo_flat['is_template'] = repo['isTemplate']
        _repo_flat['license'] = repo['licenseInfo']['name'] if repo['licenseInfo'] else None
        _repo_flat['primary_language'] = repo['primaryLanguage']['name'] if repo['primaryLanguage'] else None
        _repo_flat['topics'] = [x['topic']['name'] for x in repo['repositoryTopics']['nodes']] if repo['repositoryTopics'] else []
        _repo_flat['description'] = repo['description']
        
        global res
        res.append(_repo_flat)

    from tqdm.auto import tqdm

    async def get_repository_list():
        await create_engine()
        # repo_list = await RepositoryStats.distinct('url')

        # for x in tqdm(repo_list):

        #     name_with_owner = x.replace('https://github.com/', '')

        #     _owner, _name = name_with_owner.split('/')
        #     # quote _owner
        #     q = GraphQLQueryComponent(
        #         "query",
        #         {},
        #         None,
        #         "rateLimit {\n  cost\n  limit\n  remaining\n  resetAt\n}",
        #         GraphQLQueryComponent(
        #             "repository",
        #             {"owner": _owner, "name": _name},
        #             flatten_output,
        #             "nameWithOwner\n stargazerCount\n createdAt\n updatedAt\n pushedAt\n isArchived\n isFork\n archivedAt\n isTemplate\n licenseInfo {\n  name\n}\nprimaryLanguage {\n  name\n}\n repositoryTopics(first: 100) {\n  nodes {\n    topic {\n      name\n    }\n  }\n}\n description\n ",
        #         )
        #     )
        #     while not q.finished:
        #         s = q.gen_query(False)
        #         logging.debug(f"Running query: {s}")
        #         try:
        #             r = client.get_one(q.gen_query(False))
        #             if r is None:
        #                 logging.error("Exception while running query")
        #                 raise Exception("Exception while running query")
        #             logging.debug(f"Got response: rateLimit {r['rateLimit']}")
        #             q.update_state(r)
        #         except Exception as e:
        #             logging.error(f"Exception while updating state: {e}")
        #             logging.error(f"Response: {r}")
        #             q.finished = True

        # # save to csv
        # import csv
        # with open('repo_list.csv', 'w') as f:
        #     writer = csv.DictWriter(f, fieldnames=res[0].keys())
        #     writer.writeheader()
        #     writer.writerows(res)

        # read csv
        import pandas as pd
        df = pd.read_csv('repo_list.csv')
        df['name'] = df['url']
        df['url'] = 'https://github.com/' + df['url']
        # fill NaN to None
        df = df.where(pd.notnull(df), None)

        # parse topics to be a list of strs
        df['topics'] = df['topics'].apply(eval)
        
        res = df.to_dict(orient='records')

        async with BulkWriter() as bw:
            for x in res:
                try:
                    await Repository(**x).save(bulk_writer=bw)
                except ValidationError as e:
                    print(e)
                    print(x)
                    raise e
            
    repo_list = asyncio.run(get_repository_list())
            

    