// Bait & Tackle combat HUD. Original renderer; log data only.
uniform float4 BFTFeed < source = "bft_live"; > = float4(0,0,0,-1);
uniform float2 BFTPosition < source = "bft_position"; > = float2(8,4);
uniform float4 BFTStats[4] < source = "bft_stats"; >;
uniform float4 BFTTarget[8] < source = "bft_target"; >;
uniform float4 BFTIdentity[8] < source = "bft_identity"; >;
uniform float4 BFTThreat < source="bft_threat"; > = float4(0,0,0,0);
uniform float BFTWidth < source = "bft_width"; > = 1664;
uniform float BFTBarMax < ui_type="slider"; ui_min=10.0; ui_max=2000.0; ui_label="DPS bar reference"; > = 200.0;
texture2D BackBufferTex : COLOR;
sampler BackBufferSampler { Texture=BackBufferTex; };
texture2D FontTex < source="BFT_Font.png"; > { Width=256; Height=128; Format=RGBA8; };
sampler FontSampler { Texture=FontTex; MinFilter=POINT; MagFilter=POINT; MipFilter=POINT; };
void VS(uint id:SV_VertexID,out float4 pos:SV_Position,out float2 uv:TEXCOORD) {
 uv.x=id==2?2.0:0.0; uv.y=id==1?2.0:0.0;pos=float4(uv*float2(2,-2)+float2(-1,1),0,1);
}
bool rect(float2 p,float4 b){return all(p>=b.xy)&&all(p<b.zw);}
float stat(int n){return BFTStats[n/4][n%4];}
float glyph(float2 p,int code){
 if(!rect(p,float4(0,0,8,16))||code<33||code>126)return 0;
 int index=code-32;float2 cell=float2(index%16,index/16)*16;
 return tex2D(FontSampler,(cell+floor(p)+0.5)/float2(256,128)).r;
}
float number(float2 p,float2 origin,float value,bool decimal){
 p-=origin;if(!rect(p,float4(0,0,64,16)))return 0;
 int i=int(floor(p.x/8));float scaled=floor(max(0,value)*(decimal?10:1)+0.5);
 int code=32;
 if(decimal&&i==6)code=46;
 else {
  int exponent=decimal?(i<6?6-i:0):7-i;
  float divisor=pow(10.0,float(exponent));
  int d=int(scaled/divisor)%10;
  if(scaled>=divisor||i==(decimal?5:7)||i==7)code=48+d;
 }
 return glyph(p-float2(i*8,0),code);
}

float identity_text(float2 p){
 p-=float2(12,3);if(!rect(p,float4(0,0,192,16)))return 0;
 int i=int(floor(p.x/8));return glyph(p-float2(i*8,0),int(BFTIdentity[i/4][i%4]));
}
float target_text(float2 p){
 p-=float2(12,21);if(!rect(p,float4(0,0,192,16)))return 0;
 int i=int(floor(p.x/8));return glyph(p-float2(i*8,0),int(BFTTarget[i/4][i%4]));
}
float label0(float2 p,float2 origin){p-=origin;if(!rect(p,float4(0,0,64,16)))return 0;const int chars[8]={68,80,83,32,47,49,50,115};int i=int(floor(p.x/8));return glyph(p-float2(i*8,0),chars[i]);}
float label1(float2 p,float2 origin){p-=origin;if(!rect(p,float4(0,0,72,16)))return 0;const int chars[9]={70,73,71,72,84,32,68,80,83};int i=int(floor(p.x/8));return glyph(p-float2(i*8,0),chars[i]);}
float label2(float2 p,float2 origin){p-=origin;if(!rect(p,float4(0,0,48,16)))return 0;const int chars[6]={68,65,77,65,71,69};int i=int(floor(p.x/8));return glyph(p-float2(i*8,0),chars[i]);}
float label3(float2 p,float2 origin){p-=origin;if(!rect(p,float4(0,0,56,16)))return 0;const int chars[7]={66,73,71,71,69,83,84};int i=int(floor(p.x/8));return glyph(p-float2(i*8,0),chars[i]);}
float label4(float2 p,float2 origin){p-=origin;if(!rect(p,float4(0,0,64,16)))return 0;const int chars[8]={72,73,84,32,82,65,84,69};int i=int(floor(p.x/8));return glyph(p-float2(i*8,0),chars[i]);}
float label5(float2 p,float2 origin){p-=origin;if(!rect(p,float4(0,0,40,16)))return 0;const int chars[5]={84,65,75,69,78};int i=int(floor(p.x/8));return glyph(p-float2(i*8,0),chars[i]);}
float label6(float2 p,float2 origin){p-=origin;if(!rect(p,float4(0,0,64,16)))return 0;const int chars[8]={84,73,77,69,32,40,83,41};int i=int(floor(p.x/8));return glyph(p-float2(i*8,0),chars[i]);}
float label7(float2 p,float2 origin){p-=origin;if(!rect(p,float4(0,0,32,16)))return 0;const int chars[4]={76,73,86,69};int i=int(floor(p.x/8));return glyph(p-float2(i*8,0),chars[i]);}
float label8(float2 p,float2 origin){p-=origin;if(!rect(p,float4(0,0,32,16)))return 0;const int chars[4]={76,65,83,84};int i=int(floor(p.x/8));return glyph(p-float2(i*8,0),chars[i]);}
float label9(float2 p,float2 origin){p-=origin;if(!rect(p,float4(0,0,56,16)))return 0;const int chars[7]={78,79,32,70,69,69,68};int i=int(floor(p.x/8));return glyph(p-float2(i*8,0),chars[i]);}
float label10(float2 p,float2 origin){p-=origin;if(!rect(p,float4(0,0,48,16)))return 0;const int chars[6]={67,84,82,76,43,72};int i=int(floor(p.x/8));return glyph(p-float2(i*8,0),chars[i]);}

float hate_label(float2 p,float2 o){p-=o;if(!rect(p,float4(0,0,64,16)))return 0;const int chars[8]={72,65,84,69,32,69,83,84};int i=int(floor(p.x/8));return glyph(p-float2(i*8,0),chars[i]);}
float hate_partial(float2 p,float2 o){p-=o;if(!rect(p,float4(0,0,32,16)))return 0;const int chars[4]={80,65,82,84};int i=int(floor(p.x/8));return glyph(p-float2(i*8,0),chars[i]);}
float hate_gear(float2 p,float2 o){p-=o;if(!rect(p,float4(0,0,48,16)))return 0;const int chars[6]={69,88,80,79,82,84};int i=int(floor(p.x/8));return glyph(p-float2(i*8,0),chars[i]);}
float hate_stale(float2 p,float2 o){p-=o;if(!rect(p,float4(0,0,80,16)))return 0;const int chars[10]={83,84,65,76,69,32,71,69,65,82};int i=int(floor(p.x/8));return glyph(p-float2(i*8,0),chars[i]);}
float hate_model(float2 p,float2 o){p-=o;if(!rect(p,float4(0,0,80,16)))return 0;const int chars[10]={73,78,67,79,77,80,76,69,84,69};int i=int(floor(p.x/8));return glyph(p-float2(i*8,0),chars[i]);}
float4 PS(float4 position:SV_Position,float2 uv:TEXCOORD):SV_Target {
 float4 scene=tex2D(BackBufferSampler,uv);float2 p=uv*float2(BUFFER_WIDTH,BUFFER_HEIGHT)-BFTPosition;
 if(!rect(p,float4(0,0,BFTWidth,42)))return scene;
 float3 gold=float3(.78,.63,.3),light=float3(.92,.94,.9),muted=float3(.54,.68,.69);
 float3 color=float3(.018,.04,.047);
 if(!rect(p,float4(1,1,BFTWidth-1,41)))color=gold;
 if(identity_text(p)>.5)color=light;
 if(target_text(p)>.5)color=muted;
 if(rect(p,float4(210,6,211,35)))color=float3(.15,.28,.29);
 int columns=BFTWidth>=1500?7:(BFTWidth>=1200?5:(BFTWidth>=850?3:2));
 float step=(BFTWidth-488)/columns;
 float x=228;
 float labels=label0(p,float2(x,3));float nums=number(p,float2(x,21),stat(0),true);
 if(columns>=3){x+=step;labels=max(labels,label1(p,float2(x,3)));nums=max(nums,number(p,float2(x,21),stat(1),true));}
 x+=step;labels=max(labels,label2(p,float2(x,3)));nums=max(nums,number(p,float2(x,21),stat(2),false));
 if(columns>=5){
  x+=step;labels=max(labels,label3(p,float2(x,3)));nums=max(nums,number(p,float2(x,21),stat(4),false));
  if(columns==7){
   x+=step;labels=max(labels,label4(p,float2(x,3)));nums=max(nums,number(p,float2(x,21),stat(7),true));nums=max(nums,glyph(p-float2(x+66,21),37));
   x+=step;labels=max(labels,label5(p,float2(x,3)));nums=max(nums,number(p,float2(x,21),stat(8),false));
  }
  x+=step;labels=max(labels,label6(p,float2(x,3)));nums=max(nums,number(p,float2(x,21),stat(3),false));
 }
 if(labels>.5)color=muted;if(nums>.5)color=light;
 float hx=BFTWidth-242;
 if(rect(p,float4(hx-10,6,hx-9,35)))color=float3(.15,.28,.29);
 if(hate_label(p,float2(hx,3))>.5)color=muted;
 if(BFTFeed.w<0){if(label9(p,float2(hx,21))>.5)color=muted;}
 else if(BFTThreat.w==0){if(hate_gear(p,float2(hx,21))>.5)color=gold;}
 else if(BFTThreat.w==3){if(hate_stale(p,float2(hx,21))>.5)color=gold;}
 else if(BFTThreat.w==4){if(hate_model(p,float2(hx,21))>.5)color=gold;}
 else {
  float hn=number(p,float2(hx,21),BFTThreat.x,false);
  if(abs(BFTThreat.y-BFTThreat.x)>.5){hn=max(hn,glyph(p-float2(hx+64,21),45));hn=max(hn,number(p,float2(hx+72,21),BFTThreat.y,false));}
  if(hn>.5)color=gold;
  if(BFTThreat.w==1 && hate_partial(p,float2(hx+88,3))>.5)color=gold;
 }
 float statusx=BFTWidth-82;
 if(BFTFeed.w<0){if(label9(p,float2(statusx,3))>.5)color=float3(.9,.3,.3);}
 else if((stat(13)>.5?label7(p,float2(statusx,3)):label8(p,float2(statusx,3)))>.5)color=muted;
 if(label10(p,float2(statusx,21))>.5)color=gold;
 if(rect(p,float4(BFTWidth-18,7,BFTWidth-8,17)))color=BFTFeed.w<0?float3(.9,.15,.15):(BFTFeed.w>.5?gold:float3(.1,.8,.35));
 if(rect(p,float4(12,40,12+(BFTWidth-24)*saturate(stat(0)/max(10,BFTBarMax)),42)))color=float3(.09,.65,.5);
 return float4(color,1);
}
technique BFT_Test < ui_label="Bait & Tackle Damage Strip"; > {pass{VertexShader=VS;PixelShader=PS;}}
