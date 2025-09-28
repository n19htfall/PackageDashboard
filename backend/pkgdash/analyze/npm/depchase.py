"""分析lock文件"""

import json
import asyncio


from packageurl import PackageURL

from pkgdash.models.database.deplink import PackageDependency
from pkgdash.models.connector.mongo import create_engine

packages_dir = "/home/lzh/npm/"
package_json_path = packages_dir + "axios-1.8.4/axios-1.8.4/package.json"
lock_json_path = packages_dir + "axios-1.8.4/axios-1.8.4/package-lock.json"

if __name__ == "__main__":

    async def main():
        await create_engine()
        package_json: dict = json.load(open(package_json_path, "r", encoding="utf-8"))
        constraints: dict = package_json.get("dependencies")
        lock: dict = json.load(open(lock_json_path, "r", encoding="utf-8"))
        pkg_name = lock.get("name")
        pkg_version = lock.get("version")
        pkg_purl = PackageURL(
            name=pkg_name,
            namespace=None,
            qualifiers=None,
            subpath=None,
            type="npm",
            version=pkg_version,
        )
        dependencies: dict[str, dict] = lock.get("dependencies")
        for dep in dependencies:
            if dep in constraints:
                dep_purl = PackageURL(
                    name=dep,
                    namespace=None,
                    qualifiers=None,
                    subpath=None,
                    type="npm",
                    version=dependencies[dep].get("version"),
                )
                pd = PackageDependency(
                    purl=pkg_purl.to_string(),
                    dep_purl=dep_purl.to_string(),
                    constraint=constraints.get(dep),
                    type="npm",
                )
                print(pd)
                await pd.save()

    asyncio.run(main())
