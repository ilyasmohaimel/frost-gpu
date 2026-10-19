import fs from 'node:fs';
const html=fs.readFileSync('film.template','utf8').replace('<script type="module" src="film.js"></script>',`<script type="module">\n${fs.readFileSync('film.js','utf8')}\n</script>`);
fs.writeFileSync('index.html',html);
