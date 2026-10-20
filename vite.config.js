import {defineConfig} from 'vite';
export default defineConfig({base:'./',server:{host:'127.0.0.1',port:8876,strictPort:true,hmr:false},build:{target:'es2022'}});
