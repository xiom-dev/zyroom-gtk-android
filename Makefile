PREFIX ?= /usr
DESTDIR ?=
APP_ID = net.ryzom.zyroomgtk

LIBDIR = $(DESTDIR)$(PREFIX)/lib/zyroom-gtk
BINDIR = $(DESTDIR)$(PREFIX)/bin
APPDIR = $(DESTDIR)$(PREFIX)/share/applications
ICONDIR = $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps
METADIR = $(DESTDIR)$(PREFIX)/share/metainfo

.PHONY: all build install uninstall clean

all: build

# Compile les catalogues de traduction (.mo)
build:
	python3 build_i18n.py

install: build
	install -d $(LIBDIR)/zyroom
	cp -r zyroom/. $(LIBDIR)/zyroom/
	find $(LIBDIR) -name '__pycache__' -type d -exec rm -rf {} +
	install -d $(BINDIR)
	printf '#!/usr/bin/env python3\nimport sys\nsys.path.insert(0, "$(PREFIX)/lib/zyroom-gtk")\nfrom zyroom.app import main\nsys.exit(main())\n' > $(BINDIR)/zyroom-gtk
	chmod 755 $(BINDIR)/zyroom-gtk
	install -Dm644 data/$(APP_ID).desktop $(APPDIR)/$(APP_ID).desktop
	install -Dm644 data/$(APP_ID).svg $(ICONDIR)/$(APP_ID).svg
	install -Dm644 data/$(APP_ID).metainfo.xml $(METADIR)/$(APP_ID).metainfo.xml

uninstall:
	rm -rf $(LIBDIR)
	rm -f $(BINDIR)/zyroom-gtk
	rm -f $(APPDIR)/$(APP_ID).desktop
	rm -f $(ICONDIR)/$(APP_ID).svg
	rm -f $(METADIR)/$(APP_ID).metainfo.xml

clean:
	find zyroom -name '__pycache__' -type d -exec rm -rf {} +
