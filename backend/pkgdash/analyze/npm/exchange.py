from packageurl import PackageURL
from pkgdash.models.database.deplink import PackageDependency
import asyncio
from pkgdash.models.connector.mongo import create_engine
import json
from pymongo.errors import DuplicateKeyError

output_json_dir = "./pkgdash/analyze/npm/output/"


async def iterate_packages() -> None:
    async for pd in PackageDependency.find_all():
        if pd.type != "npm":
            continue
        dep_purl = PackageURL.from_string(pd.dep_purl)
        purl = PackageURL.from_string(pd.purl)
        if dep_purl.namespace is not None and dep_purl.name.startswith("@"):
            dep_purl = dep_purl._replace(namespace=dep_purl.name, name=dep_purl.namespace)
        if purl.namespace is not None and purl.name.startswith("@"):
            purl = purl._replace(namespace=purl.name, name=purl.namespace)
        dep_purl_str = dep_purl.to_string()
        purl_str = purl.to_string()
        new_dep_purl = dep_purl._replace(version=None)
        new_dep_purl_str = new_dep_purl.to_string()

        if purl.namespace is None:
            scancode_json = f"{purl.name}-{purl.version}.json"
            if scancode_json == "encrypt-storage-2.14.06.json":
                scancode_json = "encrypt-storage-2.14.6.json"
        else:
            scancode_json = f"{purl.namespace}_{purl.name}-{purl.version}.json"

        output: dict = json.load(open(output_json_dir + scancode_json, "r", encoding="utf-8"))
        dep_lst: list[dict] = output.get("dependencies")
        con = None
        if dep_lst:
            for dep in dep_lst:
                if dep.get("purl") == new_dep_purl_str:
                    con = dep.get("extracted_requirement")
                    if con is not None:
                        print(f"更新约束, {new_dep_purl_str}")
                    break
        try:
            await pd.update(
                {
                    "$set": {
                        "dep_purl": dep_purl_str,
                        "purl": purl_str,
                        "constraint": con,
                    }
                }
            )
            print(f"更新pd {dep_purl_str} for {purl}")
        except DuplicateKeyError as e:
            pass


async def main():
    await create_engine()
    await iterate_packages()


asyncio.run(main())
