from typing import Optional, List, Union, Literal
from datetime import datetime, timedelta
from beanie import BulkWriter

from dateutil.relativedelta import relativedelta
from aiochclient import ChClient

from pkgdash.common import DATE_RANGE
from pkgdash import logger

class RepoStatsCollector:
    def __init__(self, ch_client: ChClient, name_with_owner: str, range: DATE_RANGE="Month"):
        self.ch_client = ch_client
        self.name_with_owner = name_with_owner
        self.range = range
        
        self.min_time = None
        self.max_time = None

    async def _get_by_range(self, query: str):
        results = await self.ch_client.fetch(' '.join((
            f"SELECT toStartOf{self.range}(created_at) AS start_from, COUNT(*) AS count FROM github_events",
            query,
            f"AND repo_name = '{self.name_with_owner}'",
            "GROUP BY start_from"
        )))
        return self._agg_results(results)
    
    def _agg_results(self, results):
        results = [
             (res['start_from'], res['count'])
                for res in results
        ]

        for time, count in results:
            if self.min_time is None or time < self.min_time:
                self.min_time = time
            if self.max_time is None or time > self.max_time:
                self.max_time = time

        return results

        # # don't fill the gap here

        # _dict_res = {}
        # _min = None
        # _max = None
        # for r in results:
        #     time: datetime = r['start_from']
        #     if _min is None or time < _min:
        #         _min = time
        #     if _max is None or time > _max:
        #         _max = time
        #     _dict_res[time] = r['count']

        # _cur = _min
        # while _cur < _max:
        #     if _cur not in _dict_res:
        #         _dict_res[_cur] = 0
        #     match self.range:
        #         case "Day":
        #             _cur += timedelta(days=1)
        #         case "Week":
        #             _cur += timedelta(weeks=1)
        #         case "Month":
        #             _cur += relativedelta(months=1)
        #         case "Year":
        #             _cur += relativedelta(years=1)
        # return _dict_res

    def fill_gap(self, results):
        _dict_res = {}
        for time, count in results:
            _dict_res[time] = count

        _cur = self.min_time
        while _cur <= self.max_time:
            if _cur not in _dict_res:
                _dict_res[_cur] = 0
            match self.range:
                case "Day":
                    _cur += timedelta(days=1)
                case "Week":
                    _cur += timedelta(weeks=1)
                case "Month":
                    _cur += relativedelta(months=1)
                case "Year":
                    _cur += relativedelta(years=1)
        return _dict_res

    async def get_n_comments(self):
        return await self._get_by_range((
            " WHERE event_type = 'IssueCommentEvent'"
            " AND action = 'created'"
        ))

    async def get_n_commits(self):
        results = await self.ch_client.fetch((
            f" SELECT toStartOf{self.range}(created_at) AS start_from, SUM(push_distinct_size) AS count FROM github_events"
            " WHERE event_type = 'PushEvent'"
            f" AND repo_name = '{self.name_with_owner}'"
            " GROUP BY start_from"
        ))
        return self._agg_results(results)

    async def get_n_issues(self) :
            return await self._get_by_range((
            " WHERE event_type = 'IssuesEvent'"
            " AND action = 'opened'"
        ))

    async def get_n_prs(self) :
            return await self._get_by_range((
            " WHERE event_type = 'PullRequestEvent'"
            " AND action = 'opened'"
        ))

    async def get_n_stars(self) :
            return await self._get_by_range((
            " WHERE event_type = 'WatchEvent'"
        ))

    async def get_n_tags(self) :
            return await self._get_by_range((
            " WHERE event_type = 'CreateEvent'"
            " AND ref_type = 'tag'"
        ))
    
def _date_to_datetime(d) -> datetime:
    args = d.timetuple()[:6]
    return datetime(*args)

async def _get_repo_hits(ch_client: ChClient, name: str, owner: str):
    # convert to date
    res = await ch_client.fetch((
        "SELECT * FROM ght_hits.repo_weights"
        f" WHERE name_with_owner = '{owner}/{name}'"
    ))
    d_res = {}
    for r in res:
        d_res[_date_to_datetime(r['beforeYearMonth']) - relativedelta(months=1)] = (r['weight'], r['weight_zscore'], r['weight_rank_pct'])
    return d_res
    
if __name__ == '__main__':
    import asyncio
    import re
    from aiohttp import ClientSession
    from pkgdash.models.connector.clickhouse import create_engine

    from pkgdash.models.connector.mongo import create_engine as create_mongo

    from pkgdash.models.database.repository import RepositoryStats
    from pkgdash.models.database.sourcelink import PackageSource
    from tqdm.auto import tqdm

    GITHUB_PATTERN = re.compile(r'^https://github.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)/?$')

    async def main():
        await create_mongo()

        async with ClientSession() as s:
            ch_client = await create_engine(s)

            # await RepositoryStats.delete_all()

            # for source in tqdm(await PackageSource.find_all().to_list()):
            #     _grouped = GITHUB_PATTERN.match(source.repo_url)
            #     owner, name = _grouped[1], _grouped[2]

            #     collector = RepoStatsCollector(ch_client, f"{owner}/{name}", "Month")

            #     commits = await collector.get_n_commits()
            #     comments = await collector.get_n_comments()
            #     issues = await collector.get_n_issues()
            #     prs = await collector.get_n_prs()
            #     stars = await collector.get_n_stars()
            #     tags = await collector.get_n_tags()

            #     # logger.info("Collecting stats for {}/{} from {} to {}", owner, name, collector.min_time, collector.max_time)

            #     if collector.min_time is None:
            #         continue

            #     d_commits = collector.fill_gap(commits)
            #     d_comments = collector.fill_gap(comments)
            #     d_prs = collector.fill_gap(prs)
            #     d_issues = collector.fill_gap(issues)
            #     d_stars = collector.fill_gap(stars)
            #     d_tags = collector.fill_gap(tags)

            #     async with BulkWriter() as writer:
            #         for date in d_comments.keys():
            #             rcd = RepositoryStats(
            #                 stats_from=_date_to_datetime(date),
            #                 stats_interval="Month",
            #                 url=source.repo_url,
            #                 n_commits=d_commits[date],
            #                 n_comments=d_comments[date],
            #                 n_issues=d_issues[date],
            #                 n_prs=d_prs[date],
            #                 n_stars=d_stars[date],
            #                 n_tags=d_tags[date],
            #             )
            #             await rcd.save(bulk_writer=writer)

            COUNT = 1
            _total = await RepositoryStats.count()

            async with BulkWriter() as writer:
                async for repo_stats in RepositoryStats.find_all():
                    _grouped = GITHUB_PATTERN.match(repo_stats.url)
                    owner, name = _grouped[1], _grouped[2]

                    COUNT += 1
                    if COUNT % 1000 == 0:
                        logger.info("Processed {}/{} records", COUNT, _total)
                        writer.commit()

                    hits_rcd = await _get_repo_hits(ch_client, name, owner, repo_stats.stats_from)
                    
                    if not hits_rcd:
                        continue

                    repo_stats.hits = hits_rcd["weight"]
                    repo_stats.hits_zscore = hits_rcd["weight_zscore"]
                    repo_stats.hits_rank_pct = hits_rcd["weight_rank_pct"]
                    # await repo_stats.save(bulk_writer=writer)

    asyncio.run(main())