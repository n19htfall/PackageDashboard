import requests
import json


def get_npm_package_info(package_name):
    # 构建npm registry API的URL
    url = f"https://registry.npmjs.org/{package_name}"

    # 发送GET请求
    response = requests.get(url)

    # 检查请求是否成功
    if response.status_code == 200:
        # 解析JSON响应
        package_info = response.json()

        # 获取repository和homepage信息
        repository = package_info.get("repository", {})
        homepage = package_info.get("homepage", "")

        print(f"Package: {package_name}")
        print(f"Repository: {repository}")
        print(f"Homepage: {homepage}")

        return repository, homepage
    else:
        print(f"Error: Unable to fetch package information. Status code: {response.status_code}")
        return None, None


# 使用示例
if __name__ == "__main__":
    package_name = "lodash"  # 替换为你想查询的包名
    get_npm_package_info(package_name)
