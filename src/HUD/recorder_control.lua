obs = obslua
local command_path, status_path = '', ''
local last_command, last_clip, error_text = '', '', ''
local ready, tick_count = false, 0
local function write_status()
 local f=io.open(status_path,'w')
 if f then
  local src=obs.obs_get_source_by_name('BFT EQ capture')
  local width=src and obs.obs_source_get_width(src) or 0
  local height=src and obs.obs_source_get_height(src) or 0
  if src then obs.obs_source_release(src) end
  f:write(last_command..'\n'..(obs.obs_frontend_replay_buffer_active() and 'active' or 'idle')..'\n'..last_clip..'\n'..error_text..'\n'..tostring(width)..'\n'..tostring(height)..'\n');f:close()
 end
end
local function setup()
 -- No desktop, microphone, browser, streaming or game-hook sources.
 for i=1,6 do obs.obs_set_output_source(i,nil) end
 local scene_src=obs.obs_get_source_by_name('BFT Evidence')
 if not scene_src then local scene=obs.obs_scene_create('BFT Evidence');scene_src=obs.obs_scene_get_source(scene);obs.obs_source_addref(scene_src);obs.obs_scene_release(scene) end
 local scene=obs.obs_scene_from_source(scene_src)
 local src=obs.obs_get_source_by_name('BFT EQ capture')
 if not src then
  local settings=obs.obs_data_create()
  obs.obs_data_set_string(settings,'window','EverQuest:_EverQuestwndclass:eqgame.exe')
  obs.obs_data_set_int(settings,'method',2)
  obs.obs_data_set_int(settings,'priority',0)
  obs.obs_data_set_bool(settings,'client_area',true)
  obs.obs_data_set_bool(settings,'cursor',true)
  obs.obs_data_set_bool(settings,'capture_audio',true)
  src=obs.obs_source_create('window_capture','BFT EQ capture',settings,nil);obs.obs_data_release(settings)
  if src then obs.obs_scene_add(scene,src) end
 end
 if src then
  local item=obs.obs_scene_find_source(scene,'BFT EQ capture')
  if item then local info=obs.obs_video_info();obs.obs_get_video_info(info);local size=obs.vec2();size.x=info.base_width;size.y=info.base_height;obs.obs_sceneitem_set_bounds_type(item,obs.OBS_BOUNDS_SCALE_INNER);obs.obs_sceneitem_set_bounds(item,size) end
  obs.obs_source_release(src)
 else error_text='EQ window capture could not be created.' end
 obs.obs_frontend_set_current_scene(scene_src);obs.obs_source_release(scene_src)
 obs.obs_frontend_set_preview_enabled(false)
 ready=true
end
local function tick()
 tick_count=tick_count+1
 if not ready then local ok,err=pcall(setup);if not ok then error_text=tostring(err) end end
 local f=io.open(command_path,'r')
 if f then
  local seq=f:read('*l');local action=f:read('*l');f:close()
  if seq and seq~=last_command and ready then
   last_command=seq
   if action=='start' then obs.obs_frontend_replay_buffer_start()
   elseif action=='stop' then obs.obs_frontend_replay_buffer_stop()
   elseif action=='save' and obs.obs_frontend_replay_buffer_active() then obs.obs_frontend_replay_buffer_save()
   elseif action=='screenshot' then obs.obs_frontend_take_screenshot()
   end
  end
 end
 write_status()
end
local function event(e)
 if e==obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_SAVED then last_clip=obs.obs_frontend_get_last_replay() or '';write_status() end
end
function script_description() return 'Bait & Tackle five-minute EQ-only replay buffer. No microphone or desktop audio.' end
function script_load(settings)
 command_path=obs.obs_data_get_string(settings,'command_path');status_path=obs.obs_data_get_string(settings,'status_path');obs.obs_frontend_add_event_callback(event);obs.timer_add(tick,500)
end
function script_unload() obs.timer_remove(tick) end
