import { asyncRequest } from './request'

export async function getRepositoryList(page?: number, size?: number) {
  return await asyncRequest<Page<Repository>>({
    url: '/api/repo/list',
    method: 'get',
    data: {
      page,
      size,
    },
  })
}

export async function searchRepositoryList(regex: string, page?: number, size?: number) {
  return await asyncRequest<Page<Repository>>({
    url: '/api/repo/search',
    method: 'get',
    data: {
      q: regex,
      page,
      size,
    },
  })
}

export async function getRepositoryInfo(url: string) {
  return await asyncRequest<Repository>({
    url: '/api/repo/info',
    method: 'get',
    data: {
      url,
    },
  })
}

export async function getRepositoryStats(url: string) {
  return await asyncRequest<RepositoryStats[]>({
    url: '/api/repo/stats',
    method: 'get',
    data: {
      url,
    },
  })
}

export async function getRepositoryPackages(url: string) {
  return await asyncRequest<PackageSource[]>({
    url: '/api/repo/packages',
    method: 'get',
    data: {
      url,
    },
  })
}
