/**
  CNC Bridge — Anilam Crusader M Post Processor for Autodesk Fusion 360
  
  Enhanced post processor for Anilam Crusader M (Crusader II series) CNC mills.
  Supports G29 subroutine system, T10xx tool table format, Anilam-specific
  drilling cycles with V-variables, M1000/M2000 look-ahead mode, and
  DNC-friendly output formatting.

  Based on Anilam ISO post (Autodesk) with extensive Crusader M enhancements
  derived from the UPE post definition (MY72.89) and RS232/programming manuals.

  Compatible Controllers:
    - Anilam Crusader M  (default — 4800 baud, 7-bit, XON/XOFF)
    - Anilam Crusader II (select via controllerModel property — 2400 baud, no parity, no handshake)
  
  Both controllers share the same RS-274-D G-code dialect including G29
  subroutines, V-variables, M1000/M2000 look-ahead, and canned cycles.
  The only differences are RS232 communication defaults.

  Machine: Anilam Crusader M / Crusader II (3-axis milling)
  Controller: Anilam Crusader II / M series
  Communication: RS232 serial (DNC drip feed supported)
  
  Copyright (C) 2026 CNC Bridge Project
  FORKID {A1B2C3D4-5678-90AB-CDEF-CRUSADERM001}
*/

description = "Anilam Crusader M - CNC Bridge";
vendor = "CNC Bridge";
vendorUrl = "https://github.com/Apocscode/CNC-Bridge";
legal = "Copyright (C) 2026 CNC Bridge Project";
certificationLevel = 2;
minimumRevision = 24000;

longDescription = "Enhanced post processor for Anilam Crusader M and Crusader II CNC milling controllers. " +
  "Supports G29 subroutine calls, T10xx tool table format, Anilam-specific drilling cycles " +
  "with V-variables, M1000/M2000 look-ahead mode, and DNC-friendly output. " +
  "Select controller model in properties to auto-configure RS232 defaults. " +
  "Designed for use with the CNC Bridge serial communication system.";

extension = "txt";
setCodePage("ascii");

capabilities = CAPABILITY_MILLING;
tolerance = spatial(0.002, MM);

minimumChordLength = spatial(0.01, MM);
minimumCircularRadius = spatial(0.01, MM);
maximumCircularRadius = spatial(1000, MM);
minimumCircularSweep = toRad(0.01);
maximumCircularSweep = toRad(180);
allowHelicalMoves = true;
allowedCircularPlanes = (1 << PLANE_XY) | (1 << PLANE_ZX) | (1 << PLANE_YZ);

// ============================================================================
// User-Configurable Properties
// ============================================================================
// ============================================================================
// Controller Model Profiles
// ============================================================================
var controllerProfiles = {
  "crusader-m": {
    name: "Anilam Crusader M",
    baud: 4800,
    dataBits: 7,
    parity: "even",
    handshake: "xon-xoff",
    auxBaud: "AUX 2787",
    auxBits: "AUX 2767",
    auxParity: "AUX 2772",
    auxHandshake: "AUX 2791",
    auxReceive: "AUX 2701",
    notes: "Default — Supermax-30 / Crusader M settings"
  },
  "crusader-ii": {
    name: "Anilam Crusader II",
    baud: 2400,
    dataBits: 7,
    parity: "none",
    handshake: "none",
    auxBaud: "AUX 2786",
    auxBits: "AUX 2767",
    auxParity: "AUX 2770",
    auxHandshake: "AUX 2790",
    auxReceive: "AUX 2701",
    notes: "Bridgeport Crusader II — older LED display controllers"
  }
};

properties = {
  // --- Controller Model ---
  controllerModel: "crusader-m",  // "crusader-m" or "crusader-ii"
  
  // --- Output Formatting ---
  showSequenceNumbers: true,
  sequenceNumberStart: 0,
  sequenceNumberIncrement: 2,
  separateWordsWithSpace: false,
  
  // --- Comments ---
  writeComments: true,
  writeMachine: true,
  writeTools: true,
  writeProgramName: true,
  writeOperationComments: true,
  writeToolComments: true,
  writeTimestamp: true,
  writeFileStats: true,
  
  // --- Machine Limits ---
  maxSpindleRPM: 10000,
  maxFeedRate: 500,  // IPM
  
  // --- Tool Change ---
  toolChangeZ: 0,
  homeOnToolChange: true,
  
  // --- Operation ---
  optionalStop: false,
  useLookAhead: true,         // M1000/M2000 look-ahead mode for contouring
  useSubroutines: false,      // Use G29 subroutines for repeated patterns
  
  // --- DNC / Communication ---
  dncMode: false,             // Optimize output for DNC drip feed
  addPercentSigns: true,      // Wrap program with % signs
  addProgramEnd: true,        // Add program end marker
  
  // --- Arc Output ---
  useArcIJFormat: true,       // true = IJ incremental, false = R format
  
  // --- Coolant ---
  useCoolant: true
};

// ============================================================================
// Format Definitions — Anilam Crusader M specific
// ============================================================================
var numberOfToolSlots = 99;

var gFormat = createFormat({prefix:"G", decimals:0});
var mFormat = createFormat({prefix:"M", decimals:0});
var hFormat = createFormat({prefix:"H", decimals:0});
var dFormat = createFormat({prefix:"D", decimals:0});
var tFormat = createFormat({prefix:"T", decimals:0, width:2, zeropad:true});

var xyzFormat = createFormat({decimals:(unit == MM ? 3 : 4)});
var abcFormat = createFormat({decimals:3, forceDecimal:true, scale:DEG});
var feedFormat = createFormat({decimals:(unit == MM ? 1 : 2)});
var toolFormat = createFormat({decimals:0, width:2, zeropad:true});
var rpmFormat = createFormat({decimals:0});
var secFormat = createFormat({decimals:1, forceDecimal:true});
var taperFormat = createFormat({decimals:1, scale:DEG});

// Variable outputs
var xOutput = createVariable({prefix:"X"}, xyzFormat);
var yOutput = createVariable({prefix:"Y"}, xyzFormat);
var zOutput = createVariable({prefix:"Z"}, xyzFormat);
var aOutput = createVariable({prefix:"A"}, abcFormat);
var bOutput = createVariable({prefix:"B"}, abcFormat);
var cOutput = createVariable({prefix:"C"}, abcFormat);
var feedOutput = createVariable({prefix:"F"}, feedFormat);
var sOutput = createVariable({prefix:"S", force:true}, rpmFormat);
var dOutput = createVariable({}, dFormat);

// Circular output — incremental IJ
var iOutput = createReferenceVariable({prefix:"I"}, xyzFormat);
var jOutput = createReferenceVariable({prefix:"J"}, xyzFormat);
var kOutput = createReferenceVariable({prefix:"K"}, xyzFormat);

// Modal groups
var gMotionModal = createModal({}, gFormat);                                          // G0-G3
var gPlaneModal = createModal({onchange:function(){gMotionModal.reset();}}, gFormat); // G17-19
var gAbsIncModal = createModal({}, gFormat);                                          // G90-91
var gFeedModeModal = createModal({}, gFormat);                                        // G94-95
var gUnitModal = createModal({}, gFormat);                                            // G70-71
var gCycleModal = createModal({}, gFormat);                                           // G81, etc.
var gRetractModal = createModal({}, gFormat);                                         // G98-99

// ============================================================================
// State Tracking
// ============================================================================
var sequenceNumber;
var currentWorkOffset;
var currentWorkPlaneABC = undefined;
var currentMachineABC;
var closestABC = false;
var pendingRadiusCompensation = -1;
var lookAheadActive = false;
var retracted = false;
var subroutineTag = 0;

// Coolant map: [flood, mist, through-tool]
var mapCoolantTable = new Table(
  [8, 7, 8],
  {initial:COOLANT_OFF, force:true},
  "Invalid coolant mode"
);

// ============================================================================
// Helper Functions
// ============================================================================

/** Write a block with optional sequence numbers. */
function writeBlock() {
  if (properties.showSequenceNumbers) {
    writeWords2("N" + sequenceNumber, arguments);
    sequenceNumber += properties.sequenceNumberIncrement;
  } else {
    writeWords(arguments);
  }
}

/** Write a block without sequence number. */
function writeBlockNoSeq() {
  writeWords(arguments);
}

/** Format a comment string. */
function formatComment(text) {
  return "( " + String(text).replace(/[\(\)]/g, " ") + " )";
}

/** Write a comment line. */
function writeComment(text) {
  if (properties.writeComments) {
    writeln(formatComment(text));
  }
}

/** Clamp feed rate to machine maximum. */
function clampFeed(feed) {
  var maxFeed = (unit == MM) ? (properties.maxFeedRate * 25.4) : properties.maxFeedRate;
  return Math.min(feed, maxFeed);
}

/** Clamp spindle RPM to machine maximum. */
function clampRPM(rpm) {
  return Math.min(rpm, properties.maxSpindleRPM);
}

/** Force output of X, Y, and Z. */
function forceXYZ() {
  xOutput.reset();
  yOutput.reset();
  zOutput.reset();
}

/** Force output of A, B, and C. */
function forceABC() {
  aOutput.reset();
  bOutput.reset();
  cOutput.reset();
}

/** Force output of all motion variables. */
function forceAny() {
  forceXYZ();
  forceABC();
  feedOutput.reset();
}

function forceWorkPlane() {
  currentWorkPlaneABC = undefined;
}

/** Activate M1000 look-ahead mode. */
function enableLookAhead() {
  if (properties.useLookAhead && !lookAheadActive) {
    writeBlock(mFormat.format(1000));
    lookAheadActive = true;
  }
}

/** Deactivate M2000 look-ahead mode. */
function disableLookAhead() {
  if (properties.useLookAhead && lookAheadActive) {
    writeBlock(mFormat.format(2000));
    lookAheadActive = false;
  }
}

/** Write coolant on command. */
function setCoolant(coolant) {
  if (!properties.useCoolant) { return; }
  if (coolant == COOLANT_OFF) {
    writeBlock(mFormat.format(9));
  } else {
    try {
      var c = mapCoolantTable.lookup(coolant);
      writeBlock(mFormat.format(c));
    } catch (e) {
      writeBlock(mFormat.format(8)); // default to flood
    }
  }
}

/** Write G29 subroutine start. */
function writeSubroutineStart(tag) {
  writeBlock(gFormat.format(29), "S" + tag);
}

/** Write G29 subroutine call. */
function writeSubroutineCall(tag) {
  writeBlock(gFormat.format(29), "C" + tag);
}

/** Write G29 subroutine end + return. */
function writeSubroutineEnd() {
  writeBlock(gFormat.format(29), "E");
}

/** Write the tool change sequence using G29 C1. */
function writeToolChange() {
  writeBlock(gFormat.format(29), "C1");
}

// ============================================================================
// Work Plane (Multi-axis support)
// ============================================================================

function setWorkPlane(abc) {
  if (!machineConfiguration.isMultiAxisConfiguration()) {
    return;
  }
  if (!((currentWorkPlaneABC == undefined) ||
        abcFormat.areDifferent(abc.x, currentWorkPlaneABC.x) ||
        abcFormat.areDifferent(abc.y, currentWorkPlaneABC.y) ||
        abcFormat.areDifferent(abc.z, currentWorkPlaneABC.z))) {
    return;
  }
  onCommand(COMMAND_UNLOCK_MULTI_AXIS);
  writeBlock(
    gMotionModal.format(0),
    conditional(machineConfiguration.isMachineCoordinate(0), "A" + abcFormat.format(abc.x)),
    conditional(machineConfiguration.isMachineCoordinate(1), "B" + abcFormat.format(abc.y)),
    conditional(machineConfiguration.isMachineCoordinate(2), "C" + abcFormat.format(abc.z))
  );
  onCommand(COMMAND_LOCK_MULTI_AXIS);
  currentWorkPlaneABC = abc;
}

function getWorkPlaneMachineABC(workPlane) {
  var W = workPlane;
  var abc = machineConfiguration.getABC(W);
  if (closestABC) {
    if (currentMachineABC) {
      abc = machineConfiguration.remapToABC(abc, currentMachineABC);
    } else {
      abc = machineConfiguration.getPreferredABC(abc);
    }
  } else {
    abc = machineConfiguration.getPreferredABC(abc);
  }
  try {
    abc = machineConfiguration.remapABC(abc);
    currentMachineABC = abc;
  } catch (e) {
    error(
      localize("Machine angles not supported") + ":" +
      conditional(machineConfiguration.isMachineCoordinate(0), " A" + abcFormat.format(abc.x)) +
      conditional(machineConfiguration.isMachineCoordinate(1), " B" + abcFormat.format(abc.y)) +
      conditional(machineConfiguration.isMachineCoordinate(2), " C" + abcFormat.format(abc.z))
    );
  }
  var direction = machineConfiguration.getDirection(abc);
  if (!isSameDirection(direction, W.forward)) {
    error(localize("Orientation not supported."));
  }
  if (!machineConfiguration.isABCSupported(abc)) {
    error(
      localize("Work plane is not supported") + ":" +
      conditional(machineConfiguration.isMachineCoordinate(0), " A" + abcFormat.format(abc.x)) +
      conditional(machineConfiguration.isMachineCoordinate(1), " B" + abcFormat.format(abc.y)) +
      conditional(machineConfiguration.isMachineCoordinate(2), " C" + abcFormat.format(abc.z))
    );
  }
  var tcp = true;
  if (tcp) {
    setRotation(W);
  } else {
    var O = machineConfiguration.getOrientation(abc);
    var R = machineConfiguration.getRemainingOrientation(abc, W);
    setRotation(R);
  }
  return abc;
}

// ============================================================================
// Program Start — onOpen
// ============================================================================

function onOpen() {
  // Disable unused rotary axes
  if (!machineConfiguration.isMachineCoordinate(0)) { aOutput.disable(); }
  if (!machineConfiguration.isMachineCoordinate(1)) { bOutput.disable(); }
  if (!machineConfiguration.isMachineCoordinate(2)) { cOutput.disable(); }

  if (!properties.separateWordsWithSpace) {
    setWordSeparator("");
  }

  sequenceNumber = properties.sequenceNumberStart;

  // --- Program header ---
  if (properties.addPercentSigns) {
    writeln("%");
  }

  // Resolve controller profile
  var profile = controllerProfiles[properties.controllerModel] || controllerProfiles["crusader-m"];

  // Program comments
  if (properties.writeComments) {
    if (properties.writeProgramName && programName) {
      writeComment("PROGRAM: " + programName);
    }
    if (programComment) {
      writeComment(programComment);
    }
    writeComment("FORMAT: " + profile.name + " - CNC Bridge Post");
    writeComment("CONTROLLER: " + profile.name);
    writeComment("RS232: " + profile.baud + " baud, " + profile.dataBits + "-bit, " + profile.parity + " parity, " + profile.handshake + " handshake");
    writeComment("AUX SETUP: " + profile.auxBaud + ", " + profile.auxBits + ", " + profile.auxParity + ", " + profile.auxHandshake + ", " + profile.auxReceive);
    if (properties.writeTimestamp) {
      var d = new Date();
      writeComment(d.toLocaleDateString() + " AT " + d.toLocaleTimeString());
    }
    writeComment("OUTPUT IN " + ((unit == MM) ? "METRIC" : "ABSOLUTE ENGLISH"));
    if (properties.dncMode) {
      writeComment("DNC DRIP FEED MODE");
    }
  }

  // Machine info
  if (properties.writeMachine) {
    var mVendor = machineConfiguration.getVendor();
    var mModel = machineConfiguration.getModel();
    var mDesc = machineConfiguration.getDescription();
    if (mVendor || mModel || mDesc) {
      writeComment("Machine");
      if (mVendor) { writeComment("  Vendor: " + mVendor); }
      if (mModel) { writeComment("  Model: " + mModel); }
      if (mDesc) { writeComment("  Description: " + mDesc); }
    }
  }

  // --- Initialization block: G0 G70/G71 G90 G29 ---
  switch (unit) {
    case IN:
      writeBlock("N0", gFormat.format(0), gUnitModal.format(70), gAbsIncModal.format(90), gFormat.format(29));
      break;
    case MM:
      writeBlock("N0", gFormat.format(0), gUnitModal.format(71), gAbsIncModal.format(90), gFormat.format(29));
      break;
  }
  // Reset sequence number after the N0 init block
  sequenceNumber = properties.sequenceNumberStart + properties.sequenceNumberIncrement;

  // --- Tool table: T10xx Xdia Zlength ---
  if (properties.writeTools) {
    var tools = getToolTable();
    if (tools.getNumberOfTools() > 0) {
      for (var i = 0; i < tools.getNumberOfTools(); ++i) {
        var tool = tools.getTool(i);
        var toolNum = toolFormat.format(tool.number);
        writeBlock(
          "T10" + toolNum,
          "X" + xyzFormat.format(tool.diameter),
          "Z" + xyzFormat.format(tool.bodyLength > 0 ? tool.bodyLength : tool.lengthOffset)
        );
      }
    }
  }

  // --- Tool change subroutine (G29 C1 / S1) ---
  // Define the tool change return subroutine at program start
  writeToolChange();

  // Write tool change subroutine definition
  writeSubroutineStart(1);
  writeBlock("T0");                                              // Deselect tool
  writeBlock(mFormat.format(5));                                 // Spindle off
  writeBlock(gAbsIncModal.format(90), gFormat.format(0),
    "Z" + xyzFormat.format(properties.toolChangeZ));             // Retract Z
  if (properties.homeOnToolChange) {
    writeBlock(gAbsIncModal.format(90), gFormat.format(0),
      "X" + xyzFormat.format(0), "Y" + xyzFormat.format(0));    // Home XY
  }
  writeSubroutineEnd();

  subroutineTag = 1; // Tag 1 is reserved for tool change
}

// ============================================================================
// Event Handlers
// ============================================================================

function onComment(message) {
  writeComment(message);
}

function onParameter(name, value) {
  // Reserved for future parameter handling
}

// ============================================================================
// Section Start — onSection (Operation Start)
// ============================================================================

function onSection() {
  var insertToolCall = isFirstSection() ||
    (currentSection.getForceToolChange && currentSection.getForceToolChange()) ||
    (tool.number != getPreviousSection().getTool().number);

  retracted = false;
  var newWorkOffset = isFirstSection() ||
    (getPreviousSection().workOffset != currentSection.workOffset);
  var newWorkPlane = isFirstSection() ||
    !isSameDirection(getPreviousSection().getGlobalFinalToolAxis(), currentSection.getGlobalInitialToolAxis());

  // --- Retract before tool change ---
  if (insertToolCall || newWorkOffset || newWorkPlane) {
    if (insertToolCall && !isFirstSection()) {
      // Disable look-ahead before retract
      disableLookAhead();
      // Coolant off
      setCoolant(COOLANT_OFF);
      // Spindle off
      onCommand(COMMAND_STOP_SPINDLE);
    }
    // Retract to safe Z
    writeBlock(gFormat.format(0), "Z" + xyzFormat.format(properties.toolChangeZ));
    if (properties.homeOnToolChange) {
      writeBlock(gFormat.format(0), "X" + xyzFormat.format(0), "Y" + xyzFormat.format(0));
    }
    zOutput.reset();
    retracted = true;
  }

  // --- Tool change ---
  if (insertToolCall) {
    forceWorkPlane();

    // Operation comments
    if (properties.writeOperationComments) {
      if (hasParameter("operation-comment")) {
        var comment = getParameter("operation-comment");
        if (comment) {
          writeComment("OPERATION " + (currentSection.getId() + 1) + ": " + comment);
        }
      }
    }

    // Tool comments
    if (properties.writeToolComments) {
      writeComment("TOOL " + tool.number + ": " + xyzFormat.format(tool.diameter) + " " + getToolTypeName(tool.type));
      if (tool.comment) {
        writeComment(tool.comment);
      }
    }

    // Optional stop between operations
    if (!isFirstSection() && properties.optionalStop) {
      writeBlock(mFormat.format(1));
    }

    // Tool select — Anilam format: Txx
    writeBlock("T" + toolFormat.format(tool.number));
  }

  // --- Spindle on ---
  if (insertToolCall || isFirstSection() ||
      (rpmFormat.areDifferent(tool.spindleRPM, sOutput.getCurrent())) ||
      (tool.clockwise != getPreviousSection().getTool().clockwise)) {
    var rpm = clampRPM(tool.spindleRPM);
    if (rpm < 1) {
      error(localize("Spindle speed out of range."));
    }
    if (rpm > properties.maxSpindleRPM) {
      warning(localize("Spindle speed exceeds maximum, clamped to " + properties.maxSpindleRPM + " RPM."));
    }
    writeBlock(mFormat.format(tool.clockwise ? 3 : 4));
  }

  // --- Coolant on ---
  if (insertToolCall) {
    setCoolant(tool.coolant);
  }

  // --- Work offset ---
  if (insertToolCall) {
    currentWorkOffset = undefined;
  }
  var workOffset = currentSection.workOffset;
  if (workOffset == 0) { workOffset = 1; }
  if (workOffset != currentWorkOffset) {
    // Anilam Crusader M does not support standard G54-G59 work offsets
    // Use M1101 + origin position for multi-part offset if needed
    currentWorkOffset = workOffset;
  }

  // --- Work plane ---
  forceXYZ();
  if (machineConfiguration.isMultiAxisConfiguration()) {
    var abc = new Vector(0, 0, 0);
    if (currentSection.isMultiAxis()) {
      forceWorkPlane();
      cancelTransformation();
    } else {
      abc = getWorkPlaneMachineABC(currentSection.workPlane);
    }
    setWorkPlane(abc);
  } else {
    var remaining = currentSection.workPlane;
    if (!isSameDirection(remaining.forward, new Vector(0, 0, 1))) {
      error(localize("Tool orientation is not supported."));
      return;
    }
    setRotation(remaining);
  }

  // --- Initial positioning ---
  forceAny();
  var initialPosition = getFramePosition(currentSection.getInitialPosition());

  if (!retracted) {
    if (getCurrentPosition().z < initialPosition.z) {
      writeBlock(gMotionModal.format(0), zOutput.format(initialPosition.z));
    }
  }

  gMotionModal.reset();
  writeBlock(
    gAbsIncModal.format(90),
    gMotionModal.format(0),
    xOutput.format(initialPosition.x),
    yOutput.format(initialPosition.y),
    zOutput.format(initialPosition.z)
  );
}

// ============================================================================
// Tool Type Name Helper
// ============================================================================

function getToolTypeName(type) {
  switch (type) {
    case TOOL_DRILL: return "DRILL";
    case TOOL_DRILL_CENTER: return "CENTER DRILL";
    case TOOL_DRILL_SPOT: return "SPOT DRILL";
    case TOOL_MILLING_END_FLAT: return "FLAT ENDMILL";
    case TOOL_MILLING_END_BALL: return "BALL ENDMILL";
    case TOOL_MILLING_END_BULLNOSE: return "BULLNOSE ENDMILL";
    case TOOL_MILLING_CHAMFER: return "CHAMFER MILL";
    case TOOL_MILLING_FACE: return "FACE MILL";
    case TOOL_MILLING_SLOT: return "SLOT MILL";
    case TOOL_MILLING_RADIUS: return "RADIUS MILL";
    case TOOL_MILLING_DOVETAIL: return "DOVETAIL MILL";
    case TOOL_MILLING_TAPERED: return "TAPERED MILL";
    case TOOL_MILLING_LOLLIPOP: return "LOLLIPOP MILL";
    case TOOL_TAP_RIGHT_HAND: return "TAP RH";
    case TOOL_TAP_LEFT_HAND: return "TAP LH";
    case TOOL_REAMER: return "REAMER";
    case TOOL_BORING_BAR: return "BORING BAR";
    case TOOL_COUNTER_BORE: return "COUNTERBORE";
    case TOOL_COUNTER_SINK: return "COUNTERSINK";
    case TOOL_HOLDER_ONLY: return "HOLDER";
    case TOOL_PROBE: return "PROBE";
    default: return "UNKNOWN";
  }
}

// ============================================================================
// Dwell
// ============================================================================

function onDwell(seconds) {
  if (seconds > 99999.999) {
    warning(localize("Dwelling time is out of range."));
  }
  seconds = clamp(0.001, seconds, 99999.999);
  writeBlock(gFormat.format(4), "T" + secFormat.format(seconds));
}

function onSpindleSpeed(spindleSpeed) {
  writeBlock(sOutput.format(clampRPM(spindleSpeed)));
}

// ============================================================================
// Drilling Cycles — Anilam V-Variable Format
// ============================================================================

function onCycle() {
  writeBlock(gPlaneModal.format(17));
}

function getCommonCycle(x, y, z, r) {
  forceXYZ();
  return [xOutput.format(x), yOutput.format(y), zOutput.format(z),
          "R" + xyzFormat.format(r)];
}

/**
 * Anilam Crusader M drilling cycles use V-variables:
 * V20 = feed rate
 * V21 = clearance plane (retract)
 * V22 = dwell time
 * V23 = peck depth
 * V24 = retract clearance plane 1
 */
function onCyclePoint(x, y, z) {
  if (isFirstCyclePoint()) {
    repositionToCycleClearance(cycle, x, y, z);

    var F = clampFeed(cycle.feedrate);
    var P = (cycle.dwell == 0) ? 0 : clamp(0.001, cycle.dwell, 99999.999);

    switch (cycleType) {
      case "drilling":
        // Anilam: G29 LV20=feed V21=clearance, then G81
        writeBlock(
          gFormat.format(29),
          "LV20=" + feedFormat.format(F),
          "V21=" + xyzFormat.format(cycle.retract)
        );
        writeBlock(
          gCycleModal.format(81),
          xOutput.format(x), yOutput.format(y),
          zOutput.format(z)
        );
        break;

      case "counter-boring":
        writeBlock(
          gFormat.format(29),
          "LV20=" + feedFormat.format(F),
          "V21=" + xyzFormat.format(cycle.retract),
          conditional(P > 0, "V22=" + secFormat.format(P))
        );
        writeBlock(
          gCycleModal.format(P > 0 ? 82 : 81),
          xOutput.format(x), yOutput.format(y),
          zOutput.format(z)
        );
        break;

      case "chip-breaking":
        // Expand — Anilam doesn't have a native chip-break cycle
        expandCyclePoint(x, y, z);
        break;

      case "deep-drilling":
        // Peck drilling: G83 with V23=peck
        writeBlock(
          gFormat.format(29),
          "LV20=" + feedFormat.format(F),
          "V21=" + xyzFormat.format(cycle.retract),
          conditional(P > 0, "V22=" + secFormat.format(P)),
          "V23=" + xyzFormat.format(cycle.incrementalDepth)
        );
        if (P > 0) {
          // Use G89 with FIFO dwell variant
          writeBlock(
            gCycleModal.format(89),
            xOutput.format(x), yOutput.format(y),
            zOutput.format(z)
          );
        } else {
          writeBlock(
            gCycleModal.format(83),
            xOutput.format(x), yOutput.format(y),
            zOutput.format(z)
          );
        }
        break;

      case "tapping":
      case "right-tapping":
        // Tapping uses G29 subroutine approach on Crusader M
        if (!F) { F = tool.getTappingFeedrate(); }
        subroutineTag++;
        writeSubroutineStart(subroutineTag);
        writeBlock(gMotionModal.format(1), zOutput.format(z), feedOutput.format(F));
        writeBlock(mFormat.format(4));  // Reverse spindle
        writeBlock("Z" + xyzFormat.format(cycle.retract));
        writeBlock(mFormat.format(3));  // Forward spindle
        writeBlock(gMotionModal.format(0));
        writeSubroutineEnd();
        // Position and call
        writeBlock(gMotionModal.format(0), xOutput.format(x), yOutput.format(y));
        writeSubroutineCall(subroutineTag);
        break;

      case "left-tapping":
        if (!F) { F = tool.getTappingFeedrate(); }
        subroutineTag++;
        writeSubroutineStart(subroutineTag);
        writeBlock(gMotionModal.format(1), zOutput.format(z), feedOutput.format(F));
        writeBlock(mFormat.format(3));  // Reverse for LH tap
        writeBlock("Z" + xyzFormat.format(cycle.retract));
        writeBlock(mFormat.format(4));  // Forward for LH tap
        writeBlock(gMotionModal.format(0));
        writeSubroutineEnd();
        writeBlock(gMotionModal.format(0), xOutput.format(x), yOutput.format(y));
        writeSubroutineCall(subroutineTag);
        break;

      case "reaming":
        writeBlock(
          gFormat.format(29),
          "LV20=" + feedFormat.format(F),
          "V21=" + xyzFormat.format(cycle.retract)
        );
        writeBlock(
          gCycleModal.format(85),
          xOutput.format(x), yOutput.format(y),
          zOutput.format(z)
        );
        break;

      case "boring":
        writeBlock(
          gFormat.format(29),
          "LV20=" + feedFormat.format(F),
          "V21=" + xyzFormat.format(cycle.retract),
          conditional(P > 0, "V22=" + secFormat.format(P))
        );
        writeBlock(
          gCycleModal.format(P > 0 ? 89 : 85),
          xOutput.format(x), yOutput.format(y),
          zOutput.format(z)
        );
        break;

      case "stop-boring":
        writeBlock(
          gFormat.format(29),
          "LV20=" + feedFormat.format(F),
          "V21=" + xyzFormat.format(cycle.retract),
          "V22=" + secFormat.format(P)
        );
        writeBlock(
          gCycleModal.format(86),
          xOutput.format(x), yOutput.format(y),
          zOutput.format(z)
        );
        break;

      case "fine-boring":
      case "back-boring":
      case "manual-boring":
        // Expand unsupported cycles to linear moves
        expandCyclePoint(x, y, z);
        break;

      default:
        expandCyclePoint(x, y, z);
    }
  } else {
    if (cycleExpanded) {
      expandCyclePoint(x, y, z);
    } else {
      // Subsequent hole positions
      var _x = xOutput.format(x);
      var _y = yOutput.format(y);
      if (!_x && !_y) {
        xOutput.reset();
        _x = xOutput.format(x);
      }
      writeBlock(_x, _y);
    }
  }
}

function onCycleEnd() {
  if (!cycleExpanded) {
    writeBlock(gFormat.format(80));  // Cancel canned cycle
    zOutput.reset();
  }
}

// ============================================================================
// Linear Motion — onRapid, onLinear
// ============================================================================

function onRadiusCompensation() {
  pendingRadiusCompensation = radiusCompensation;
}

function onRapid(_x, _y, _z) {
  // Disable look-ahead for rapid moves
  disableLookAhead();

  var x = xOutput.format(_x);
  var y = yOutput.format(_y);
  var z = zOutput.format(_z);
  if (x || y || z) {
    if (pendingRadiusCompensation >= 0) {
      error(localize("Radius compensation mode cannot be changed at rapid traversal."));
    }
    writeBlock(gMotionModal.format(0), x, y, z);
    feedOutput.reset();
  }
}

function onLinear(_x, _y, _z, feed) {
  // Enable look-ahead for cutting moves
  enableLookAhead();

  feed = clampFeed(feed);

  if (pendingRadiusCompensation >= 0) {
    xOutput.reset();
    yOutput.reset();
  }
  var x = xOutput.format(_x);
  var y = yOutput.format(_y);
  var z = zOutput.format(_z);
  var f = feedOutput.format(feed);

  if (x || y || z) {
    if (pendingRadiusCompensation >= 0) {
      pendingRadiusCompensation = -1;
      var d = tool.diameterOffset;
      if (d > numberOfToolSlots) {
        warning(localize("The diameter offset exceeds the maximum value."));
      }
      writeBlock(gPlaneModal.format(17));
      switch (radiusCompensation) {
        case RADIUS_COMPENSATION_LEFT:
          dOutput.reset();
          writeBlock(gMotionModal.format(1), gFormat.format(41), x, y, z, dOutput.format(d), f);
          break;
        case RADIUS_COMPENSATION_RIGHT:
          dOutput.reset();
          writeBlock(gMotionModal.format(1), gFormat.format(42), x, y, z, dOutput.format(d), f);
          break;
        default:
          writeBlock(gMotionModal.format(1), gFormat.format(40), x, y, z, f);
      }
    } else {
      writeBlock(gMotionModal.format(1), x, y, z, f);
    }
  } else if (f) {
    if (getNextRecord().isMotion()) {
      feedOutput.reset();
    } else {
      writeBlock(gMotionModal.format(1), f);
    }
  }
}

// ============================================================================
// 5-Axis Motion (stub — Crusader M is 3-axis but kept for compatibility)
// ============================================================================

function onRapid5D(_x, _y, _z, _a, _b, _c) {
  if (!currentSection.isOptimizedForMachine()) {
    error(localize("This post configuration has not been customized for 5-axis simultaneous toolpath."));
    return;
  }
  if (pendingRadiusCompensation >= 0) {
    error(localize("Radius compensation mode cannot be changed at rapid traversal."));
    return;
  }
  var x = xOutput.format(_x);
  var y = yOutput.format(_y);
  var z = zOutput.format(_z);
  var a = aOutput.format(_a);
  var b = bOutput.format(_b);
  var c = cOutput.format(_c);
  writeBlock(gMotionModal.format(0), x, y, z, a, b, c);
  feedOutput.reset();
}

function onLinear5D(_x, _y, _z, _a, _b, _c, feed) {
  if (!currentSection.isOptimizedForMachine()) {
    error(localize("This post configuration has not been customized for 5-axis simultaneous toolpath."));
    return;
  }
  if (pendingRadiusCompensation >= 0) {
    error(localize("Radius compensation cannot be activated/deactivated for 5-axis move."));
    return;
  }
  feed = clampFeed(feed);
  var x = xOutput.format(_x);
  var y = yOutput.format(_y);
  var z = zOutput.format(_z);
  var a = aOutput.format(_a);
  var b = bOutput.format(_b);
  var c = cOutput.format(_c);
  var f = feedOutput.format(feed);
  if (x || y || z || a || b || c) {
    writeBlock(gMotionModal.format(1), x, y, z, a, b, c, f);
  } else if (f) {
    if (getNextRecord().isMotion()) {
      feedOutput.reset();
    } else {
      writeBlock(gMotionModal.format(1), f);
    }
  }
}

// ============================================================================
// Circular Motion — onCircular
// ============================================================================

function onCircular(clockwise, cx, cy, cz, x, y, z, feed) {
  enableLookAhead();
  feed = clampFeed(feed);

  if (pendingRadiusCompensation >= 0) {
    error(localize("Radius compensation cannot be activated/deactivated for a circular move."));
    return;
  }

  var start = getCurrentPosition();

  if (isFullCircle()) {
    if (isHelical()) {
      linearize(tolerance);
      return;
    }
    switch (getCircularPlane()) {
      case PLANE_XY:
        writeBlock(gMotionModal.format(clockwise ? 2 : 3),
          xOutput.format(x),
          iOutput.format(cx - start.x, 0), jOutput.format(cy - start.y, 0),
          feedOutput.format(feed));
        break;
      case PLANE_ZX:
        writeBlock(gMotionModal.format(clockwise ? 2 : 3),
          zOutput.format(z),
          iOutput.format(cx - start.x, 0), kOutput.format(cz - start.z, 0),
          feedOutput.format(feed));
        break;
      case PLANE_YZ:
        writeBlock(gMotionModal.format(clockwise ? 2 : 3),
          yOutput.format(y),
          jOutput.format(cy - start.y, 0), kOutput.format(cz - start.z, 0),
          feedOutput.format(feed));
        break;
      default:
        linearize(tolerance);
    }
  } else {
    if (properties.useArcIJFormat) {
      // IJ incremental format (preferred for Anilam)
      switch (getCircularPlane()) {
        case PLANE_XY:
          writeBlock(gMotionModal.format(clockwise ? 2 : 3),
            xOutput.format(x), yOutput.format(y), zOutput.format(z),
            iOutput.format(cx - start.x, 0), jOutput.format(cy - start.y, 0),
            feedOutput.format(feed));
          break;
        case PLANE_ZX:
          writeBlock(gMotionModal.format(clockwise ? 2 : 3),
            xOutput.format(x), yOutput.format(y), zOutput.format(z),
            iOutput.format(cx - start.x, 0), kOutput.format(cz - start.z, 0),
            feedOutput.format(feed));
          break;
        case PLANE_YZ:
          writeBlock(gMotionModal.format(clockwise ? 2 : 3),
            xOutput.format(x), yOutput.format(y), zOutput.format(z),
            jOutput.format(cy - start.y, 0), kOutput.format(cz - start.z, 0),
            feedOutput.format(feed));
          break;
        default:
          linearize(tolerance);
      }
    } else {
      // R format
      var r = getCircularRadius();
      if (toDeg(getCircularSweep()) > (180 + 1e-9)) {
        r = -r; // negative radius for arcs > 180 degrees
      }
      switch (getCircularPlane()) {
        case PLANE_XY:
          writeBlock(gMotionModal.format(clockwise ? 2 : 3),
            xOutput.format(x), yOutput.format(y), zOutput.format(z),
            "R" + xyzFormat.format(r),
            feedOutput.format(feed));
          break;
        case PLANE_ZX:
          writeBlock(gMotionModal.format(clockwise ? 2 : 3),
            xOutput.format(x), yOutput.format(y), zOutput.format(z),
            "R" + xyzFormat.format(r),
            feedOutput.format(feed));
          break;
        case PLANE_YZ:
          writeBlock(gMotionModal.format(clockwise ? 2 : 3),
            xOutput.format(x), yOutput.format(y), zOutput.format(z),
            "R" + xyzFormat.format(r),
            feedOutput.format(feed));
          break;
        default:
          linearize(tolerance);
      }
    }
  }
}

// ============================================================================
// Commands
// ============================================================================

var mapCommand = {
  COMMAND_STOP: 0,
  COMMAND_OPTIONAL_STOP: 1,
  COMMAND_END: 2,
  COMMAND_SPINDLE_CLOCKWISE: 3,
  COMMAND_SPINDLE_COUNTERCLOCKWISE: 4,
  COMMAND_STOP_SPINDLE: 5,
  COMMAND_ORIENTATE_SPINDLE: 19,
  COMMAND_LOAD_TOOL: 6,
  COMMAND_COOLANT_ON: 8,
  COMMAND_COOLANT_OFF: 9
};

function onCommand(command) {
  switch (command) {
    case COMMAND_START_SPINDLE:
      onCommand(tool.clockwise ? COMMAND_SPINDLE_CLOCKWISE : COMMAND_SPINDLE_COUNTERCLOCKWISE);
      return;
    case COMMAND_LOCK_MULTI_AXIS:
      return;
    case COMMAND_UNLOCK_MULTI_AXIS:
      return;
    case COMMAND_BREAK_CONTROL:
      return;
    case COMMAND_TOOL_MEASURE:
      return;
  }
  var stringId = getCommandStringId(command);
  var mcode = mapCommand[stringId];
  if (mcode != undefined) {
    writeBlock(mFormat.format(mcode));
  } else {
    onUnsupportedCommand(command);
  }
}

// ============================================================================
// Section End — onSectionEnd
// ============================================================================

function onSectionEnd() {
  // Disable look-ahead at end of operation
  disableLookAhead();
  forceAny();
}

// ============================================================================
// Program End — onClose
// ============================================================================

function onClose() {
  // Disable look-ahead
  disableLookAhead();

  // Coolant off
  setCoolant(COOLANT_OFF);

  // Spindle off
  writeln("");
  onCommand(COMMAND_STOP_SPINDLE);

  // Retract Z
  writeBlock(gAbsIncModal.format(90), gFormat.format(0),
    "Z" + xyzFormat.format(properties.toolChangeZ));
  zOutput.reset();

  // Reset work plane
  setWorkPlane(new Vector(0, 0, 0));

  // Return to home
  if (!machineConfiguration.hasHomePositionX() && !machineConfiguration.hasHomePositionY()) {
    writeBlock(gAbsIncModal.format(90), gFormat.format(0),
      "X" + xyzFormat.format(0), "Y" + xyzFormat.format(0));
  } else {
    var homeX;
    if (machineConfiguration.hasHomePositionX()) {
      homeX = "X" + xyzFormat.format(machineConfiguration.getHomePositionX());
    }
    var homeY;
    if (machineConfiguration.hasHomePositionY()) {
      homeY = "Y" + xyzFormat.format(machineConfiguration.getHomePositionY());
    }
    writeBlock(gAbsIncModal.format(90), gFormat.format(0), homeX, homeY);
  }

  // Tool change return
  writeToolChange();

  // Program end
  writeSubroutineEnd();

  // File statistics
  if (properties.writeFileStats && properties.writeComments) {
    var endProfile = controllerProfiles[properties.controllerModel] || controllerProfiles["crusader-m"];
    writeComment("CNC Bridge Post Processor - Program Complete");
    writeComment("Controller: " + endProfile.name + " (" + endProfile.baud + " baud)");
  }

  // End of record
  if (properties.addPercentSigns) {
    writeln("%");
  }
}
