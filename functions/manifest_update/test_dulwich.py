import os
import glob
import pathlib
import yaml
import pprint
import shutil
import dulwich
from dulwich import server
from dulwich import porcelain
from dulwich.repo import Repo
import tempfile

remote_repo = 'https://github.com/rafty/eks-gitops-app-manifest'
# remote_repo = 'https://github.com/rafty/eks-gitops-app-manifest.git'
github_personal_access_token = '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'

# Todo: .gitにするかどうか？
# Todo: 環境変数から取得する
# Todo: ↑のやつ？
# github_oauth_token = 'hoge'  # Todo: ASMから取得する (github_oauth_token_nameを使う)

# tmp_dir = tempfile.mkdtemp()
tmp_dir = '/Users/aa003103/PycharmProjects/awscdk-codepipeline/tmp/repo'


def replace_image_tag(manifest):
    tag_sample = '12345'

    image = manifest['spec']['template']['spec']['containers'][0]['image']
    _list = image.rsplit(':')
    _list[1] = tag_sample
    image_value = ':'.join(_list)
    print(f'image_value: {image_value}')

    manifest['spec']['template']['spec']['containers'][0]['image'] = image_value
    return manifest


local_repo = porcelain.clone(
    source=remote_repo,
    password=github_personal_access_token,
    username='not relevant',
    target=tmp_dir,  # TODO: Lambda Local target='/tmp/repo'
    branch='master'.encode('utf-8'),
    # checkout=True,
)

# for file_ref in pathlib.Path(tmp_dir).glob('**/*'):
#     print(str(file_ref))


manifest_path = tmp_dir + '/flask_workshop/frontend/dev/flask-frontend-dep.yaml'

with open(manifest_path, 'r+', encoding='utf-8') as f:
    manifest = yaml.safe_load(f)
    pprint.pprint(manifest)
    replaced_manifest = replace_image_tag(manifest)


with open(manifest_path, 'w+', encoding='utf-8') as f:
    yaml.dump(
        data=replaced_manifest,
        stream=f,
        sort_keys=False,  # Keyの順番を維持するためにsort_key=Falseを指定
    )

with open(manifest_path, 'r', encoding='utf-8') as f:
    manifest = yaml.safe_load(f)
    pprint.pprint(manifest)

# porcelain.add()

committer = 'awscodepipeline <lambda@example.com>'

porcelain.commit(
    repo=local_repo,
    message=f'Update image tag.',
    author=committer,
    committer=committer,
)

porcelain.add(local_repo, manifest_path)

# porcelain.remote_add()

branch_name = 'master'
porcelain.push(
    repo=local_repo,
    remote_location=remote_repo,
    refspecs=branch_name.encode('utf-8'),
    password=github_personal_access_token,
    username='not relevant'
)

# Todo: delete tmp/repo
# shutil.rmtree()
