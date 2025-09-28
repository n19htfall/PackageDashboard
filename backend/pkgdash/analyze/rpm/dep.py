import os
from typing import Set, Optional, Tuple, List, Dict
from beanie import BulkWriter

import solv
from urllib.parse import quote_plus
from tqdm.auto import tqdm

from pkgdash import logger
from .depchase import fix_deps, solve, Repo, setup_pool, solve_a_package


class RPMSolver:
    """
    A collection of RPM repositories
    """
    name: str
    pool: solv.Pool

    def __init__(self,
                 name: str,
                 arch: str,
                 repos: Dict[str, str],
                 ):
        """
        Initialize a solv.Pool
        :param name: name of the package
        :param arch: arch of the package
        :param repos: list of {repo name: repo path}
        :returns: solv.Pool
        """
        self.name = name
        _repos = []
        for k, v in repos.items():
            if 'repodata' in v:
                _r = v.split('repodata')[0]
            else:
                _r = v
            _repos.append(Repo(k, _r))
        self.pool = setup_pool(arch, _repos)
        fix_deps(self.pool)
        logger.info("Initialized pool for {} {} with {} packages", name, arch, len(self.pool.solvables))

    def get_package_by_name(self, hint: str) -> Optional[solv.XSolvable]:
        """
        Find a package by name
        """
        sel = self.pool.select(hint, solv.Selection.SELECTION_NAME | solv.Selection.SELECTION_DOTARCH)
        if sel.isempty():
            logger.error("Package {} can't be found", hint)
            return None
        found = sel.solvables()
        if len(found) > 1:
            logger.warning("More matching solvables were found, {}".format(found))
        return found[0]

    def find_source(self, pkg: solv.XSolvable) -> Optional[solv.XSolvable]:
        """
        !!! CURRENTLY NOT WORKING !!!
        Find the source package of a binary package
        """
        src = pkg.lookup_sourcepkg()[:-4]
        sel = pkg.pool.select(src, solv.Selection.SELECTION_CANON | solv.Selection.SELECTION_SOURCE_ONLY)
        # TODO: fix static mapping of src -> bin repos
        sel.filter(pkg.repo.appdata.srcrepo.handle.Selection())
        if sel.isempty():
            logger.warning("Source package {} can't be found", src)
            return None
        found = sel.solvables()
        if len(found) > 1:
            logger.warning("More matching solvables for {} were found: {}", src, found)
        return found[0]

    def find_direct_deps(self, pkg: solv.XSolvable) -> Tuple[Dict[solv.XSolvable, str], Set[str]]:
        """
        Find all direct dependencies of a package by matching its requirements
        :param pool: solv.Pool
        :param pkg: solv.XSolvable
        :returns: (binary packages, unsatisfied requirements)
        """
        unsatisfied = set()
        deps = {}
        for dep in pkg.lookup_deparray(solv.SOLVABLE_REQUIRES):
            _provides_pkgs = self.pool.whatprovides(dep)
            if len(_provides_pkgs) == 0:
                logger.warning(f"No package provides {dep} required by {pkg}")
                unsatisfied.add(dep)
            else:
                deps[_provides_pkgs.pop()] = dep
        return deps, unsatisfied

    def find_runtime_deps(self, pkg: solv.XSolvable) -> Tuple[Set[solv.XSolvable], Set[solv.XSolvable]]:
        """
        !!! CURRENTLY NOT WORKING !!!
        Find all runtime dependencies of a package by simulating an installation
        :param pool: solv.Pool
        :param pkg: solv.XSolvable
        :returns: (binary packages, source packages)
        """
        solver = self.pool.Solver()
        solver.set_flag(solv.Solver.SOLVER_FLAG_IGNORE_RECOMMENDED, 1)
        binary, source = solve_a_package(solver, pkg, selfhost=True)
        return binary, source

    def find_all_deps(self, pkg: solv.XSolvable) -> Tuple[Set[solv.XSolvable], Set[solv.XSolvable]]:
        """
        !!! CURRENTLY NOT WORKING !!!
        Find all (runtime+build) dependencies of a package by simulating an installation
        :param pool: solv.Pool
        :param pkg: solv.XSolvable
        :returns: (binary packages, source packages)
        """
        solver = self.pool.Solver()
        solver.set_flag(solv.Solver.SOLVER_FLAG_IGNORE_RECOMMENDED, 1)
        binary, source = solve_a_package(solver, pkg, selfhost=False)
        return binary, source
    

def _get_canonical_repo_name(path: str, arch: str) -> str or None:
    try:
        _name = path.split("repodata")[0]
        _name = os.path.basename(os.path.dirname(_name))
        if f"_{arch}" not in _name and "_source" not in _name:
        #     _name = _name.split(f"_{arch}")[0]
        # elif "_source" in _name:
        #     _name = _name.split("_source")[0] + "-source"
        # else:
            # logger.warning(f"Can't find _{arch} or _source in {path}")
            return None
        _name = _name.replace("_", "-")
        # _name = '-'.join(_name.split('-')[:-1])
    except Exception as e:
        logger.error("Not a valid repository path: {}", path)
        raise e
    return _name

def _solvable_to_purl(solvable: solv.XSolvable, distro: str, distro_release: str) -> str:
        return (
        f"pkg:rpm/{quote_plus(distro)}/{quote_plus(solvable.name)}"
        f"@{quote_plus(solvable.evr)}?"
        f"arch={solvable.arch}&epoch=0"
        f"&distro={quote_plus(distro)}-{quote_plus(distro_release)}"
    )


if __name__ == '__main__':
    from pkgdash.fetch.rpm.meta import download_rpm_all_meta, download_rpm_repo_meta
    from pkgdash.models.connector.mongo import create_engine
    from pkgdash.models.database.osrepo import OSPackageRepository
    from pkgdash.models.database.deplink import PackageDependency

    async def main():
        await create_engine()
        await PackageDependency.delete_all()
        for osrepo in await OSPackageRepository.find().to_list():
            for arch in osrepo.archs:
                logger.info(f"Initializing solver for {osrepo.name} {arch}")

                repos = {}
                for f in osrepo.files:
                    _path = os.path.join(f.split('repodata')[0], 'repodata')
                    _name = _get_canonical_repo_name(_path, arch)
                    if _name:
                        repos[_name] = _path
                logger.info("Initialized repositories: {}", list(repos.keys()))

                solver = RPMSolver(osrepo.name, arch, repos)

                async with BulkWriter() as writer:
                    for solvable in tqdm(solver.pool.solvables_iter(), total=len(solver.pool.solvables)):
                        _solvable_purl = _solvable_to_purl(solvable, osrepo.distro, osrepo.distro_release)
                        _solvable_id = solvable.id

                        deps, unsatisfied = solver.find_direct_deps(solvable)

                        for dep, cons in deps.items():
                            _dep_purl = _solvable_to_purl(dep, osrepo.distro, osrepo.distro_release)
                            _dep_id = dep.id

                            rec = PackageDependency(
                                purl=_solvable_purl,
                                pkgid=_solvable_id,
                                dep_purl=_dep_purl,
                                dep_pkgid=_dep_id,
                                constraint=str(cons),
                                type="rpm",
                            )

                            await rec.save(bulk_writer=writer)

    import asyncio

    asyncio.run(main())

    # logger.basicConfig(level=logger.INFO)

    # fedora_repos = {
    #     "fedora-source": "https://mirrors.tuna.tsinghua.edu.cn/fedora/releases/37/Everything/source/tree/",
    #     "fedora": "https://mirrors.tuna.tsinghua.edu.cn/fedora/releases/37/Everything/x86_64/os/",
    #     "fedora-modular-source": "https://mirrors.tuna.tsinghua.edu.cn/fedora/releases/37/Modular/source/tree/",
    #     "fedora-modular": "https://mirrors.tuna.tsinghua.edu.cn/fedora/releases/37/Modular/x86_64/os/",
    #     "updates-source": "https://mirrors.tuna.tsinghua.edu.cn/fedora/updates/37/Everything/source/tree/",
    #     "updates": "https://mirrors.tuna.tsinghua.edu.cn/fedora/updates/37/Everything/x86_64/",
    #     "updates-modular-source": "https://mirrors.tuna.tsinghua.edu.cn/fedora/updates/37/Modular/source/tree/",
    #     "updates-modular": "https://mirrors.tuna.tsinghua.edu.cn/fedora/updates/37/Modular/x86_64/"
    # }

    # fedora_repos_local = {
    #     k: asyncio.run(download_rpm_all_meta(v))[0] for k, v in fedora_repos.items()
    # }

    # print(fedora_repos_local)

    # # repos = asyncio.run(download_rpm_all_meta('https://mirrors.tuna.tsinghua.edu.cn/fedora/releases/37/'))

    # rpm_repos = RPMSolveEnv('fedora-37', 'x86_64', fedora_repos_local)
    # pkg = rpm_repos.get_package_by_name('python3-requests')
    # if pkg:
    #     print(pkg)
    #     # print(rpm_repos.find_source(pkg))
    #     print(rpm_repos.find_direct_deps(pkg))
    #     # print(rpm_repos.find_runtime_deps(pkg))
    #     # print(rpm_repos.find_all_deps(pkg))
