import { defineConfig } from 'vite';
export default defineConfig({base:'/studio/',server:{port:5173,proxy:{'/api':'http://127.0.0.1:8020','/health':'http://127.0.0.1:8020'}},build:{outDir:'dist'}});
