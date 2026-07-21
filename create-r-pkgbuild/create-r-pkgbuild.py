#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup

prefix = "https://cran.r-project.org/package="
license_map = {
    'GPL (≥ 3)': 'GPLv3',
    'GPL-3': 'GPLv3',
    'GPL-2 | GPL-3 [expanded from: GPL (≥ 2)]': "GPLv3"
}

def generate_pkgbuild(pkg_name):
    cran_url = prefix + pkg_name
    response = requests.get(cran_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    #with open('./index.html') as f:
    #    html = f.read()
    #soup = BeautifulSoup(html, 'html.parser')

    def get_metadata(label):
        table = soup.find('table')
        if table is None:
            return ''
        for tr in table.find_all('tr'):
            tds = tr.find_all('td')
            if tds[0].text == label:
                return tds[1].text

    pkg_ver = get_metadata('Version:')
    description = soup.find('h2').text.split(':', 1)[1].strip()
    license = get_metadata('License:')
    if license in license_map:
        license = license_map[license]

    def parse_deps(dep_type):
        deps = []
        raw = get_metadata(dep_type)
        raw = raw if raw else ''
        deps = raw.split(',')
        deps = [i.split('(', 1)[0].strip().lower() for i in deps]
        deps = ['r-' + i for i in deps if i != 'r' and i != '']
        deps = sorted(deps)
        return deps
    depends = ['r'] + parse_deps('Imports:')
    optdepends = parse_deps('Suggests:')

    return f"""# Maintainer: Jingbei Li <i@jingbei.li>
_cranname={pkg_name}
_pkgver={pkg_ver}
pkgname=r-{pkg_name.lower()}
pkgver=${{_pkgver//-/.}}
pkgrel=1
pkgdesc="{description}"
arch=(x86_64)
url="https://cran.r-project.org/package=${{_cranname}}"
license=({license})
depends=({' '.join(depends)})
makedepends=(gcc-fortran)
optdepends=({' '.join(optdepends)})
source=("https://cran.r-project.org/src/contrib/${{_cranname}}_${{_pkgver}}.tar.gz")

build() {{
  R CMD INSTALL ${{_cranname}}_${{_pkgver}}.tar.gz -l "${{srcdir}}"
}}

package() {{
  install -dm0755 "${{pkgdir}}/usr/lib/R/library"
  cp -a --no-preserve=ownership "${{_cranname}}" "${{pkgdir}}/usr/lib/R/library"
}}
"""

if __name__ == "__main__":
    import sys

    print(generate_pkgbuild(sys.argv[1]))
