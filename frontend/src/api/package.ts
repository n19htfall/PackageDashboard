import { asyncRequest } from './request'

export async function getPackageList(page?: number, size?: number) {
  return await asyncRequest<Page<Package>>({
    url: '/api/pkg/list',
    method: 'get',
    data: {
      page,
      size,
    },
  })
}

export async function searchPackageList(regex: string, page?: number, size?: number, distros?: Array<string>) {
  return await asyncRequest<Page<Package>>({
    url: '/api/pkg/search',
    method: 'get',
    data: {
      q: regex,
      distros,
      page,
      size,
    },
  })
}

export async function getPackageInfo(purl: string) {
  return await asyncRequest<Package>({
    url: '/api/pkg/info',
    method: 'get',
    data: {
      purl,
    },
  })
}

export async function getPackageStats(purl: string) {
  return await asyncRequest<PackageStats[]>({
    url: '/api/pkg/stats',
    method: 'get',
    data: {
      purl,
    },
  })
}

export async function getPackageDependencies(purl: string) {
  return await asyncRequest<PackageDependency[]>({
    url: '/api/pkg/deps',
    method: 'get',
    data: {
      purl,
    },
  })
}

export async function getPackageTransitiveDependencies(purl: string) {
  return await asyncRequest<PackageDependency[]>({
    url: '/api/pkg/tdeps',
    method: 'get',
    data: {
      purl,
    },
  })
}

export async function getPackageDependents(purl: string) {
  return await asyncRequest<PackageDependency[]>({
    url: '/api/pkg/rdeps',
    method: 'get',
    data: {
      purl,
    },
  })
}

export async function getPackageAlerts(purl: string) {
  return await asyncRequest<PackageAlert>({
    url: '/api/pkg/alerts',
    method: 'get',
    data: {
      purl,
    },
  })
}

export async function getPackageSources(purl: string) {
  return await asyncRequest<PackageSource[]>({
    url: '/api/pkg/sources',
    method: 'get',
    data: {
      purl,
    },
  })
}

export async function getPackageDistros() {
  return await asyncRequest<string[]>({
    url: '/api/pkg/distros',
    method: 'get',
  })
}
