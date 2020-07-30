
# Rekursives Makefile: ruft die Makefiles der unterprojekte auf
%:
	cd fmtp-server; make $@
	cd fmtp-client; make $@

.PHONY: %