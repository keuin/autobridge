#!/bin/sh
COMMON_CONF=/etc/fh_common.conf
FHBOX_PATH=$(grep "FHBOX_BIN_PATH=" $COMMON_CONF | cut -d = -f 2)
MISC_PATH=$(grep "MISC_CONF_PATH=" $COMMON_CONF | cut -d = -f 2)
INTER_WEB=$FHBOX_PATH/inter_web
MOREMGT=$FHBOX_PATH/moremgt
AREA_PATH=$(grep "PRODUCT_CONF_PATH_TR069_CONTROL=" $COMMON_CONF | cut -d = -f 2)
area=$(grep "area_code=" $AREA_PATH | cut -d = -f 2)
. /rom/fhshell/web/web_gui/hgcxml_config.conf
. /rom/fhshell/web/web_gui/hgcxml_common.conf

wan_inst1=0
wan_inst2=0
internet_wan_str=
internet_str=
dail=2

calWanParameterIndex() {
  inst1=${1}
  inst2=${2}
  Enable_index=IGD_WAND_1_WANCD_${inst1}_WANPPPC_${inst2}_Enable
  eval Enable_index=\$$Enable_index
  Name_index=IGD_WAND_1_WANCD_${inst1}_WANPPPC_${inst2}_Name
  eval Name_index=\$$Name_index
  PPPC_ConnectionType=IGD_WAND_1_WANCD_${inst1}_WANPPPC_${inst2}_ConnectionType
  eval PPPC_ConnectionType=\$$PPPC_ConnectionType
  PPPC_Username=IGD_WAND_1_WANCD_${inst1}_WANPPPC_${inst2}_Username
  eval PPPC_Username=\$$PPPC_Username
  PPPC_Password=IGD_WAND_1_WANCD_${inst1}_WANPPPC_${inst2}_Password
  eval PPPC_Password=\$$PPPC_Password
  PPPC_ConnectionTrigger=IGD_WAND_1_WANCD_${inst1}_WANPPPC_${inst2}_ConnectionTrigger
  eval PPPC_ConnectionTrigger=\$$PPPC_ConnectionTrigger
  PPPC_IdleDisconnectTime=IGD_WAND_1_WANCD_${inst1}_WANPPPC_${inst2}_IdleDisconnectTime
  eval PPPC_IdleDisconnectTime=\$$PPPC_IdleDisconnectTime
}

for inst1 in 1 2 3 4 5 6 7 8; do
  for inst2 in 1 2; do
    #####PPPOE
    calWanParameterIndex ${inst1} ${inst2}
    ppp_wan_str=$($INTER_WEB get $Enable_index $Name_index $PPPC_ConnectionType $PPPC_Username $PPPC_Password)
    if echo "$ppp_wan_str" | grep -q '^1&.*INTERNET.*_R_' && echo "$ppp_wan_str" | grep -q "IP_Routed"; then
      wan_inst1=$inst1
      wan_inst2=$inst2
      dail=1
      all_wan_str="${inst1}&${inst2}&PPP&"${ppp_wan_str}
      break
    elif echo "$ppp_wan_str" | grep -q '^1&.*INTERNET.*_B_' && echo "$ppp_wan_str" | grep -q "PPPoE_Bridged"; then
      wan_inst1=$inst1
      wan_inst2=$inst2
      dail=0
      all_wan_str="${inst1}&${inst2}&PPP&"${ppp_wan_str}
      break
    fi
  done
  if [ $wan_inst1 -ne 0 ]; then
    break
  fi
done

echo "CONNTYPE=$PPPC_ConnectionType"