.PHONY: all clean upload

all: polyfill.js qrcode.alnum.min.js index.html

upload: all
	scp index.html entenschutz.html polyfill.js qrcode.alnum.min.js stuss:~/htdocs/qrona

index.html: index.html.src
	# note to myself: do not forget that pkcs8 for ssh-keygen is spki for WebCrypto
	sed "s#___PKEY___#$(shell ssh-keygen -f ../config/stuss2021_contact.pub -e -m pkcs8 | tail -n +2 | head -n -1 | tr -d '\n')#" $< > $@

qrcode.alnum.min.js: qrcode.alnum.js
	terser $< -o $@ -c -m

polyfill.js: FastestTextEncoderPolyfill.src.js promiz.js webcrypto-shim.js
	terser $^ -o $@ -c -m
	#google-closure-compiler FastestTextEncoderPolyfill.src.js promiz.js webcrypto-shim.js --js_output_file polyfill.js -O ADVANCED # much more efficient and removes dead code, but fails to keep comments properly and is picky about undeclared variables.

clean:
	-rm -f polyfill.js qrcode.alnum.min.js index.html
