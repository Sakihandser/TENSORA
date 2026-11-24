'use strict';

const {availableParallelism}=require('node:os');

function resolveCpuThreads(requested=0,automatic=8){
  if(!Number.isInteger(requested)||requested<0||requested>64)throw Error('CPU 线程数须为 0（自动）或 1–64 的整数。');
  return Math.min(requested||automatic,availableParallelism());
}

function threadedEnvironment(threads){
  return {...process.env,OMP_NUM_THREADS:String(threads),OMP_DYNAMIC:'FALSE'};
}

function meshCpuThreads(requested,elementCount,elementsPerThread){
  return resolveCpuThreads(requested,Math.max(1,Math.min(8,Math.round(elementCount/elementsPerThread))));
}

module.exports={resolveCpuThreads,meshCpuThreads,threadedEnvironment};
