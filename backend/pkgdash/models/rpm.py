from sqlalchemy import Column, Integer, Text
from sqlalchemy.ext.declarative import declarative_base

from urllib.parse import quote_plus

Base = declarative_base()

class RPMPackage(Base):
    __tablename__ = 'packages'
    
    pkgKey = Column(Integer, primary_key=True)
    pkgId = Column(Text)
    name = Column(Text)
    arch = Column(Text)
    version = Column(Text)
    epoch = Column(Text)
    release = Column(Text)
    summary = Column(Text)
    description = Column(Text)
    url = Column(Text)
    time_file = Column(Integer)
    time_build = Column(Integer)
    rpm_license = Column(Text)
    rpm_vendor = Column(Text)
    rpm_group = Column(Text)
    rpm_buildhost = Column(Text)
    rpm_sourcerpm = Column(Text)
    rpm_header_start = Column(Integer)
    rpm_header_end = Column(Integer)
    rpm_packager = Column(Text)
    size_package = Column(Integer)
    size_installed = Column(Integer)
    size_archive = Column(Integer)
    location_href = Column(Text)
    location_base = Column(Text)
    checksum_type = Column(Text)

    def generate_purl(self, distro: str, release: str) -> str:
        return (
            f"pkg:rpm/{quote_plus(distro)}/{quote_plus(self.name)}"
            f"@{quote_plus(self.version)}-{quote_plus(self.release)}?"
            f"arch={quote_plus(self.arch)}&epoch={quote_plus(self.epoch)}"
            f"&distro={quote_plus(distro)}-{quote_plus(release)}"
        )
