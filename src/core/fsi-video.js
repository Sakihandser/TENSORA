(function(root){
  'use strict';
  const supported=canvas=>Boolean(canvas&&root.VideoEncoder&&root.VideoFrame);
  const text=new TextEncoder();
  const bytes=(...parts)=>{
    const buffer=new Uint8Array(parts.reduce((sum,part)=>sum+part.length,0));
    let at=0;
    for(const part of parts){buffer.set(part,at);at+=part.length;}
    return buffer;
  };
  function integer(value,width=1){
    const data=new Uint8Array(width);
    for(let i=width-1;i>=0;i--){data[i]=value%256;value=Math.floor(value/256);}
    return data;
  }
  const identifier=value=>integer(value,Math.max(1,Math.ceil(Math.log2(value+1)/8)));
  function element(id,...payload){
    const size=payload.reduce((sum,part)=>sum+part.length,0);
    let width=1;
    while(size>=2**(7*width)-1)width++;
    return bytes(identifier(id),integer(size+2**(7*width),width),...payload);
  }
  const uint=(id,value)=>element(id,identifier(value));
  const string=(id,value)=>element(id,text.encode(value));
  function webmHeader(width,height,fps,frameCount){
    const duration=new Uint8Array(8);
    new DataView(duration.buffer).setFloat64(0,1000*frameCount/fps);
    const ebml=element(0x1a45dfa3,uint(0x4286,1),uint(0x42f7,1),uint(0x42f2,4),uint(0x42f3,8),
      string(0x4282,'webm'),uint(0x4287,4),uint(0x4285,2));
    const info=element(0x1549a966,uint(0x2ad7b1,1000000),element(0x4489,duration),string(0x4d80,'TENSORA'),string(0x5741,'TENSORA'));
    const video=element(0xe0,uint(0xb0,width),uint(0xba,height));
    const track=element(0xae,uint(0xd7,1),uint(0x73c5,1),uint(0x83,1),uint(0x9c,0),
      string(0x86,'V_VP8'),uint(0x23e383,Math.round(1e9/fps)),video);
    // Unknown segment size permits streaming while the output file is written.
    return bytes(ebml,identifier(0x18538067),Uint8Array.of(0x01,255,255,255,255,255,255,255),info,element(0x1654ae6b,track));
  }
  async function save({canvas,frameCount,fps,renderFrame,caption,progress}){
    if(!supported(canvas))throw Error('当前浏览器不支持视频导出。');
    const handle=await root.chooseExportFile('TENSORA-FSI.webm','video/webm','.webm');
    if(!handle)return false;
    await root.writeExportFile(handle,async writer=>{
      const staging=document.createElement('canvas');
      const ratio=Math.min(1,1920/canvas.width,1080/canvas.height);
      staging.width=Math.max(2,Math.floor(canvas.width*ratio/2)*2);
      staging.height=Math.max(2,Math.floor(canvas.height*ratio/2)*2);
      const {width,height}=staging,context=staging.getContext('2d');
      const config={codec:'vp8',width,height,framerate:fps,bitrate:6000000,latencyMode:'realtime',hardwareAcceleration:'prefer-software'};
      if(!(await VideoEncoder.isConfigSupported(config)).supported)throw Error('当前浏览器不支持 VP8 视频编码。');
      await writer.write(webmHeader(width,height,fps,frameCount));
      let failure=null,cluster=[],clusterTime=0,writes=Promise.resolve(),count=0;
      function flushCluster(){
        if(!cluster.length)return;
        const data=element(0x1f43b675,uint(0xe7,clusterTime),...cluster);
        writes=writes.then(()=>writer.write(data)).catch(error=>{failure=error;});
        cluster=[];
      }
      const encoder=new VideoEncoder({
        output(chunk){
          const time=Math.round(chunk.timestamp/1000),key=chunk.type==='key';
          if(key||time-clusterTime>=30000)flushCluster();
          if(!cluster.length)clusterTime=time;
          const encoded=new Uint8Array(chunk.byteLength);
          chunk.copyTo(encoded);
          const delta=time-clusterTime;
          const block=Uint8Array.of(0x81,delta>>8,delta&255,key?0x80:0);
          cluster.push(element(0xa3,block,encoded));
          count++;
        },
        error(error){failure=error;}
      });
      try{
        encoder.configure(config);
        for(let index=0;index<frameCount;index++){
          if(failure)throw failure;
          await renderFrame(index,()=>{
            context.drawImage(canvas,0,0,width,height);
            const title=caption?.(index);
            if(title){
              context.font='14px Segoe UI, sans-serif';
              context.fillStyle='rgba(18,33,45,.80)';
              context.fillRect(12,12,Math.min(width-24,context.measureText(title).width+22),30);
              context.fillStyle='#fff';context.fillText(title,23,32,width-46);
            }
            const timestamp=Math.round(index*1e6/fps);
            const frame=new VideoFrame(staging,{timestamp,duration:Math.round((index+1)*1e6/fps)-timestamp});
            try{encoder.encode(frame,{keyFrame:index%fps===0});}finally{frame.close();}
          });
          if(encoder.encodeQueueSize>8){await encoder.flush();await writes;}
          progress?.(index+1,frameCount);
        }
        await encoder.flush();
        flushCluster();await writes;
        if(failure)throw failure;
        if(count!==frameCount)throw Error('视频帧未完整编码。');
      }finally{if(encoder.state!=='closed')encoder.close();}
    });
    return true;
  }
  root.FsiVideo={supported,save};
})(globalThis);
