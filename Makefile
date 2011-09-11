prefix=/usr/local
LIBDIR=$(prefix)/lib
BINDIR=$(prefix)/bin
DATADIR=$(prefix)/share
LOCALEDIR=$(DATADIR)/locale
MANDIR=$(DATADIR)/man

all: Makefile
	cd src/ && python3 ../setup.py build_ext --inplace

clean:
	find ./ -name \*.pyc -delete
	find ./ -name \*~ -delete
	find ./ -name "#*#" -delete

install:
	mkdir -p $(DESTDIR)$(prefix)
	install -d $(DESTDIR)$(LOCALEDIR) $(DESTDIR)$(BINDIR) $(DESTDIR)$(DATADIR)/poezio $(DESTDIR)$(DATADIR)/poezio/data $(DESTDIR)$(DATADIR)/poezio/src/ $(DESTDIR)$(DATADIR)/poezio/src $(DESTDIR)$(DATADIR)/poezio/data/themes $(DESTDIR)$(MANDIR)/man1

	cp -R data/* $(DESTDIR)$(DATADIR)/poezio/data/
	rm $(DESTDIR)$(DATADIR)/poezio/data/poezio.1

	install -m644 data/poezio.1 $(DESTDIR)$(MANDIR)/man1/
	for sourcefile in `ls -1 src/*.py src/*.so` ; do \
		install -m644 $$sourcefile $(DESTDIR)$(DATADIR)/poezio/src; \
	done

	echo "#!/usr/bin/env sh" > $(DESTDIR)$(BINDIR)/poezio
	echo "python3 $(DATADIR)/poezio/src/poezio.py \$$@" >> $(DESTDIR)$(BINDIR)/poezio
	chmod 755 $(DESTDIR)$(BINDIR)/poezio

uninstall:
	rm -f $(DESTDIR)$(BINDIR)/poezio
	rm -rf $(DESTDIR)$(DATADIR)/poezio
	rm -rf $(DESTDIR)$(MANDIR)/man1/poezio.1

pot:
	xgettext src/*.py --from-code=utf-8 --keyword=_ -o locale/poezio.pot
