import 'dart:io';
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:open_file/open_file.dart';
import 'package:path_provider/path_provider.dart';

import 'services/api_service.dart';

void main() {
  runApp(const EcuAiApp());
}

class EcuAiApp extends StatelessWidget {
  const EcuAiApp({super.key});

  @override
  Widget build(BuildContext context) {
    const seed = Color(0xFF2563EB);

    return MaterialApp(
      title: 'ECU AI App',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: seed,
          brightness: Brightness.light,
        ),
        scaffoldBackgroundColor: const Color(0xFFF5F7FB),
        useMaterial3: true,
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: Colors.white,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: Color(0xFFD9E0EC)),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: Color(0xFFD9E0EC)),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: seed, width: 1.5),
          ),
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 14,
          ),
        ),
        filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(
            minimumSize: const Size.fromHeight(48),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
        ),
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
            minimumSize: const Size(0, 46),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
            side: const BorderSide(color: Color(0xFFC9D4E5)),
          ),
        ),
      ),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  static const double _mobileBreakpoint = 720;

  final api = ApiService();

  final rpmController = TextEditingController();
  final boostController = TextEditingController();
  final injectionController = TextEditingController();
  final afrController = TextEditingController();
  final displacementController = TextEditingController();
  final stockHpController = TextEditingController();
  final mapTextController = TextEditingController();

  String fuelType = 'diesel';
  String inputMode = 'file';
  String calibrationMapType = 'soi';
  bool isTurbo = true;

  bool loadingParse = false;
  bool loadingCalibrationAnalyze = false;
  bool loadingAnalyze = false;
  bool loadingFuelMap = false;
  bool loadingReport = false;

  String? errorMessage;

  double? stage1GainPercent;
  String? potentialClass;
  double? estimatedHpAfterStage1;

  Map<String, dynamic>? fuelMapResult;
  Map<String, dynamic>? calibrationResult;
  Map<String, dynamic>? derivedFeatures;
  Map<String, dynamic>? parsedCalibrationMap;
  String? calibrationError;
  String? originalCalibrationFileName;
  Uint8List? originalCalibrationBytes;
  String? modifiedCalibrationFileName;
  Uint8List? modifiedCalibrationBytes;
  String? definitionsCalibrationFileName;
  Uint8List? definitionsCalibrationBytes;
  String? selectedMapFileName;
  String? selectedBinaryEcuFileName;
  Uint8List? selectedBinaryEcuBytes;
  String? savedPdfPath;
  int mobileTabIndex = 0;

  double? parseNumber(String value) {
    final normalized = value.trim().replaceAll(',', '.');
    if (normalized.isEmpty) return null;
    return double.tryParse(normalized);
  }

  Map<String, dynamic>? asStringMap(dynamic value) {
    if (value is Map) {
      return Map<String, dynamic>.from(value);
    }
    return null;
  }

  Map<String, dynamic> buildInputData() {
    final input = <String, dynamic>{
      'engine_displacement': parseNumber(displacementController.text),
      'fuel_type': fuelType,
      'is_turbo': isTurbo,
      'stock_hp': stockHpController.text.trim().isEmpty
          ? null
          : parseNumber(stockHpController.text),
    };

    if (inputMode == 'file' && parsedCalibrationMap != null) {
      input['calibration_map'] = parsedCalibrationMap;
    } else if (inputMode == 'paste' &&
        mapTextController.text.trim().isNotEmpty) {
      input['calibration_map_text'] = mapTextController.text.trim();
      input['calibration_map_type'] = calibrationMapType;
    } else {
      input['rpm'] = parseNumber(rpmController.text);
      input['boost_pressure'] = parseNumber(boostController.text);
      input['injection_quantity'] = parseNumber(injectionController.text);
      input['afr'] = parseNumber(afrController.text);
    }

    return input;
  }

  Future<({String name, Uint8List bytes})?> pickCalibrationFile([
    List<String>? extensions,
  ]) async {
    final picked = await FilePicker.platform.pickFiles(
      type: extensions == null ? FileType.any : FileType.custom,
      allowedExtensions: extensions,
      withData: true,
    );

    if (picked == null || picked.files.isEmpty) {
      return null;
    }

    final file = picked.files.single;
    final path = file.path;
    final bytes =
        file.bytes ?? (path == null ? null : await File(path).readAsBytes());
    if (bytes == null) {
      throw Exception('Nu am putut citi fisierul selectat.');
    }
    return (name: file.name, bytes: bytes);
  }

  Future<void> selectCalibrationOriginal() async {
    try {
      final file = await pickCalibrationFile();
      if (file == null) return;
      setState(() {
        originalCalibrationFileName = file.name;
        originalCalibrationBytes = file.bytes;
        calibrationResult = null;
        calibrationError = null;
      });
    } catch (e) {
      setState(() {
        calibrationError = 'Eroare la fisierul original: $e';
      });
    }
  }

  Future<void> selectCalibrationModified() async {
    try {
      final file = await pickCalibrationFile();
      if (file == null) return;
      setState(() {
        modifiedCalibrationFileName = file.name;
        modifiedCalibrationBytes = file.bytes;
        calibrationResult = null;
        calibrationError = null;
      });
    } catch (e) {
      setState(() {
        calibrationError = 'Eroare la fisierul modificat: $e';
      });
    }
  }

  Future<void> selectCalibrationDefinitions() async {
    try {
      final file = await pickCalibrationFile(['csv', 'json', 'kp']);
      if (file == null) return;
      setState(() {
        definitionsCalibrationFileName = file.name;
        definitionsCalibrationBytes = file.bytes;
        calibrationResult = null;
        calibrationError = null;
      });
    } catch (e) {
      setState(() {
        calibrationError = 'Eroare la definitii: $e';
      });
    }
  }

  void clearCalibrationOutputs() {
    calibrationResult = null;
    calibrationError = null;
    savedPdfPath = null;
    stage1GainPercent = null;
    potentialClass = null;
    estimatedHpAfterStage1 = null;
    derivedFeatures = null;
  }

  void removeCalibrationOriginal() {
    setState(() {
      originalCalibrationFileName = null;
      originalCalibrationBytes = null;
      clearCalibrationOutputs();
    });
  }

  void removeCalibrationModified() {
    setState(() {
      modifiedCalibrationFileName = null;
      modifiedCalibrationBytes = null;
      clearCalibrationOutputs();
    });
  }

  void removeCalibrationDefinitions() {
    setState(() {
      definitionsCalibrationFileName = null;
      definitionsCalibrationBytes = null;
      clearCalibrationOutputs();
    });
  }

  Future<void> analyzeCalibrationFiles() async {
    FocusScope.of(context).unfocus();

    final originalName = originalCalibrationFileName;
    final originalBytes = originalCalibrationBytes;
    final modifiedName = modifiedCalibrationFileName;
    final modifiedBytes = modifiedCalibrationBytes;
    if (originalName == null || originalBytes == null) {
      setState(() {
        calibrationError = 'Incarca fisierul original inainte de analiza.';
      });
      return;
    }

    setState(() {
      loadingCalibrationAnalyze = true;
      calibrationError = null;
    });

    try {
      final result = await api.analyzeCalibration(
        originalFileName: originalName,
        originalBytes: originalBytes,
        modifiedFileName: modifiedName,
        modifiedBytes: modifiedBytes,
        definitionsFileName: definitionsCalibrationFileName,
        definitionsBytes: definitionsCalibrationBytes,
        engineDisplacement: parseNumber(displacementController.text),
        fuelType: fuelType,
        isTurbo: isTurbo,
        stockHp: parseNumber(stockHpController.text),
      );

      setState(() {
        calibrationResult = result;
        final estimate = asStringMap(result['power_estimate']);
        if (estimate != null && estimate['available'] == true) {
          stage1GainPercent = (estimate['stage1_gain_percent'] as num?)
              ?.toDouble();
          potentialClass = estimate['potential_class']?.toString();
          estimatedHpAfterStage1 =
              (estimate['estimated_hp_after_stage1'] as num?)?.toDouble();
          derivedFeatures = asStringMap(estimate['derived_inputs']);
        } else {
          stage1GainPercent = null;
          potentialClass = null;
          estimatedHpAfterStage1 = null;
          derivedFeatures = null;
        }
        if (MediaQuery.sizeOf(context).width < _mobileBreakpoint) {
          mobileTabIndex = 1;
        }
      });
    } catch (e) {
      setState(() {
        calibrationError = 'Eroare la analiza calibrarii: $e';
      });
    } finally {
      setState(() {
        loadingCalibrationAnalyze = false;
      });
    }
  }

  Future<void> importMapFile() async {
    FocusScope.of(context).unfocus();

    setState(() {
      loadingParse = true;
      errorMessage = null;
    });

    try {
      final picked = await FilePicker.platform.pickFiles(
        type: FileType.any,
        withData: true,
      );

      if (picked == null || picked.files.isEmpty) {
        return;
      }

      final file = picked.files.single;
      final path = file.path;
      final bytes =
          file.bytes ?? (path == null ? null : await File(path).readAsBytes());
      if (bytes == null) {
        throw Exception('Nu am putut citi fisierul selectat.');
      }

      try {
        final result = await api.parseMapFile(
          fileName: file.name,
          bytes: bytes,
          mapType: calibrationMapType,
          fuelType: fuelType,
          isTurbo: isTurbo,
        );

        setState(() {
          selectedMapFileName = result['file_name']?.toString() ?? file.name;
          selectedBinaryEcuFileName = null;
          selectedBinaryEcuBytes = null;
          parsedCalibrationMap = asStringMap(result['calibration_map']);
          derivedFeatures = asStringMap(result['derived_features']);
          stage1GainPercent = null;
          potentialClass = null;
          estimatedHpAfterStage1 = null;
          fuelMapResult = null;
          calibrationResult = null;
          savedPdfPath = null;
        });

        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Harta importata: ${file.name}')),
        );
        return;
      } catch (_) {
        setState(() {
          selectedMapFileName = file.name;
          selectedBinaryEcuFileName = file.name;
          selectedBinaryEcuBytes = bytes;
          parsedCalibrationMap = null;
          derivedFeatures = null;
          stage1GainPercent = null;
          potentialClass = null;
          estimatedHpAfterStage1 = null;
          fuelMapResult = null;
          calibrationResult = null;
          savedPdfPath = null;
        });
      }

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Fisier ECU binar importat: ${file.name}')),
      );
    } catch (e) {
      setState(() {
        errorMessage = 'Eroare la importul hartii: $e';
      });
    } finally {
      setState(() {
        loadingParse = false;
      });
    }
  }

  Future<void> analyzeData() async {
    FocusScope.of(context).unfocus();
    final showResultsAfterAnalyze =
        MediaQuery.sizeOf(context).width < _mobileBreakpoint;

    setState(() {
      loadingAnalyze = true;
      errorMessage = null;
    });

    try {
      if (inputMode == 'file' && selectedBinaryEcuBytes != null) {
        final calibration = await api.analyzeCalibration(
          originalFileName: selectedBinaryEcuFileName ?? selectedMapFileName!,
          originalBytes: selectedBinaryEcuBytes!,
          definitionsFileName: definitionsCalibrationFileName,
          definitionsBytes: definitionsCalibrationBytes,
          engineDisplacement: parseNumber(displacementController.text),
          fuelType: fuelType,
          isTurbo: isTurbo,
          stockHp: parseNumber(stockHpController.text),
        );
        final estimate = asStringMap(calibration['power_estimate']);

        if (estimate == null || estimate['available'] != true) {
          setState(() {
            calibrationResult = calibration;
            stage1GainPercent = null;
            potentialClass = null;
            estimatedHpAfterStage1 = null;
            derivedFeatures = null;
            if (showResultsAfterAnalyze) {
              mobileTabIndex = 1;
            }
          });
          return;
        }

        setState(() {
          calibrationResult = calibration;
          stage1GainPercent = (estimate['stage1_gain_percent'] as num?)
              ?.toDouble();
          potentialClass = estimate['potential_class']?.toString();
          estimatedHpAfterStage1 =
              (estimate['estimated_hp_after_stage1'] as num?)?.toDouble();
          derivedFeatures = asStringMap(estimate['derived_inputs']);
          if (showResultsAfterAnalyze) {
            mobileTabIndex = 1;
          }
        });
        return;
      }

      final result = await api.analyze(buildInputData());

      setState(() {
        stage1GainPercent = (result['stage1_gain_percent'] as num?)?.toDouble();
        potentialClass = result['potential_class']?.toString();
        estimatedHpAfterStage1 = (result['estimated_hp_after_stage1'] as num?)
            ?.toDouble();
        derivedFeatures = asStringMap(result['derived_features']);
        calibrationResult = null;
        if (showResultsAfterAnalyze) {
          mobileTabIndex = 1;
        }
      });
    } catch (e) {
      setState(() {
        errorMessage = 'Eroare la analiza: $e';
      });
    } finally {
      setState(() {
        loadingAnalyze = false;
      });
    }
  }

  Future<void> generateFuelMap() async {
    FocusScope.of(context).unfocus();
    final showOutputAfterGenerate =
        MediaQuery.sizeOf(context).width < _mobileBreakpoint;

    setState(() {
      loadingFuelMap = true;
      errorMessage = null;
    });

    try {
      final result = await api.fuelMap(buildInputData());

      setState(() {
        fuelMapResult = result;
        stage1GainPercent ??= (result['stage1_gain_percent'] as num?)
            ?.toDouble();
        potentialClass ??= result['potential_class']?.toString();
        derivedFeatures = asStringMap(result['derived_features']);
        if (showOutputAfterGenerate) {
          mobileTabIndex = 2;
        }
      });

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Fuel map generat cu succes.')),
      );
    } catch (e) {
      setState(() {
        errorMessage = 'Eroare la generarea fuel map: $e';
      });
    } finally {
      setState(() {
        loadingFuelMap = false;
      });
    }
  }

  Future<void> generatePdfReport() async {
    FocusScope.of(context).unfocus();

    setState(() {
      loadingReport = true;
      errorMessage = null;
    });

    try {
      final originalName = originalCalibrationFileName;
      final originalBytes = originalCalibrationBytes;
      final useCalibrationReport =
          originalName != null && originalBytes != null;
      final bytes = useCalibrationReport
          ? await api.calibrationReport(
              originalFileName: originalName,
              originalBytes: originalBytes,
              modifiedFileName: modifiedCalibrationFileName,
              modifiedBytes: modifiedCalibrationBytes,
              definitionsFileName: definitionsCalibrationFileName,
              definitionsBytes: definitionsCalibrationBytes,
              engineDisplacement: parseNumber(displacementController.text),
              fuelType: fuelType,
              isTurbo: isTurbo,
              stockHp: parseNumber(stockHpController.text),
            )
          : await api.report(buildInputData());
      final fileName = useCalibrationReport
          ? 'calibration_tuner_report.pdf'
          : 'stage1_report.pdf';

      final directory = await getApplicationDocumentsDirectory();
      final file = File('${directory.path}${Platform.pathSeparator}$fileName');
      await file.writeAsBytes(bytes, flush: true);

      setState(() {
        savedPdfPath = file.path;
      });

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('PDF salvat in: ${file.path}'),
          action: SnackBarAction(
            label: 'Open',
            onPressed: () {
              OpenFile.open(file.path);
            },
          ),
        ),
      );
    } catch (e) {
      setState(() {
        errorMessage = 'Eroare la generarea PDF-ului: $e';
      });
    } finally {
      setState(() {
        loadingReport = false;
      });
    }
  }

  @override
  void dispose() {
    rpmController.dispose();
    boostController.dispose();
    injectionController.dispose();
    afrController.dispose();
    displacementController.dispose();
    stockHpController.dispose();
    mapTextController.dispose();
    super.dispose();
  }

  Widget buildTextField(
    String label,
    TextEditingController controller, {
    String? hint,
    String? suffix,
  }) {
    return TextField(
      controller: controller,
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        suffixText: suffix,
      ),
    );
  }

  List<dynamic> asList(dynamic value) {
    return value is List ? value : const [];
  }

  String formatFileSize(int? bytes) {
    if (bytes == null) return '-';
    if (bytes >= 1024 * 1024) {
      return '${(bytes / (1024 * 1024)).toStringAsFixed(2)} MB';
    }
    if (bytes >= 1024) {
      return '${(bytes / 1024).toStringAsFixed(1)} KB';
    }
    return '$bytes B';
  }

  Widget buildCalibrationFileButton({
    required String label,
    required String? fileName,
    required IconData icon,
    required VoidCallback onPressed,
    required VoidCallback onClear,
    bool optional = false,
  }) {
    return _CalibrationFilePicker(
      label: label,
      fileName: fileName,
      icon: icon,
      optional: optional,
      disabled: loadingCalibrationAnalyze,
      onPressed: onPressed,
      onClear: onClear,
    );
  }

  Widget buildInputForm(bool busy) {
    final engineFields = [
      buildTextField(
        'Engine Displacement',
        displacementController,
        hint: '2.0',
        suffix: 'L',
      ),
      buildTextField('Stock HP', stockHpController, hint: '150', suffix: 'hp'),
    ];

    return _SectionPanel(
      icon: Icons.tune_rounded,
      title: 'Calibration Input',
      subtitle:
          'Analizeaza originalul cu map pack si compara cu tuned cand exista.',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          LayoutBuilder(
            builder: (context, constraints) {
              final isWide = constraints.maxWidth >= 760;
              final width = isWide
                  ? (constraints.maxWidth - 28) / 3
                  : constraints.maxWidth;
              return Wrap(
                spacing: 14,
                runSpacing: 14,
                children: [
                  SizedBox(
                    width: width,
                    child: buildCalibrationFileButton(
                      label: 'Original calibration',
                      fileName: originalCalibrationFileName,
                      icon: Icons.source_rounded,
                      onPressed: selectCalibrationOriginal,
                      onClear: removeCalibrationOriginal,
                    ),
                  ),
                  SizedBox(
                    width: width,
                    child: buildCalibrationFileButton(
                      label: 'Tuned/current file',
                      fileName: modifiedCalibrationFileName,
                      icon: Icons.compare_arrows_rounded,
                      onPressed: selectCalibrationModified,
                      onClear: removeCalibrationModified,
                      optional: true,
                    ),
                  ),
                  SizedBox(
                    width: width,
                    child: buildCalibrationFileButton(
                      label: 'Map pack / definitions',
                      fileName: definitionsCalibrationFileName,
                      icon: Icons.list_alt_rounded,
                      onPressed: selectCalibrationDefinitions,
                      onClear: removeCalibrationDefinitions,
                      optional: true,
                    ),
                  ),
                ],
              );
            },
          ),
          const SizedBox(height: 14),
          const _InlineNotice(
            icon: Icons.info_outline_rounded,
            text:
                'Cu doar original + map pack pot sugera directii de tuning. Cu tuned/current pot compara ce s-a schimbat deja si pot estima riscuri pe zone.',
            color: Color(0xFF475569),
          ),
          const SizedBox(height: 16),
          LayoutBuilder(
            builder: (context, constraints) {
              final isWide = constraints.maxWidth >= 680;
              return Wrap(
                spacing: 14,
                runSpacing: 14,
                children: [
                  for (final field in engineFields)
                    SizedBox(
                      width: isWide
                          ? (constraints.maxWidth - 14) / 2
                          : constraints.maxWidth,
                      child: field,
                    ),
                ],
              );
            },
          ),
          const SizedBox(height: 16),
          LayoutBuilder(
            builder: (context, constraints) {
              final isWide = constraints.maxWidth >= 620;
              return Wrap(
                spacing: 14,
                runSpacing: 14,
                children: [
                  SizedBox(
                    width: isWide
                        ? (constraints.maxWidth - 14) / 2
                        : constraints.maxWidth,
                    child: DropdownButtonFormField<String>(
                      initialValue: fuelType,
                      decoration: const InputDecoration(
                        labelText: 'Fuel Type',
                        prefixIcon: Icon(Icons.local_gas_station_rounded),
                      ),
                      items: const [
                        DropdownMenuItem(
                          value: 'diesel',
                          child: Text('Diesel'),
                        ),
                        DropdownMenuItem(
                          value: 'petrol',
                          child: Text('Petrol'),
                        ),
                      ],
                      onChanged: busy
                          ? null
                          : (value) {
                              if (value == null) return;
                              setState(() {
                                fuelType = value;
                              });
                            },
                    ),
                  ),
                  SizedBox(
                    width: isWide
                        ? (constraints.maxWidth - 14) / 2
                        : constraints.maxWidth,
                    child: Container(
                      height: 56,
                      padding: const EdgeInsets.symmetric(horizontal: 14),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: const Color(0xFFD9E0EC)),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.speed_rounded),
                          const SizedBox(width: 12),
                          const Expanded(
                            child: Text(
                              'Turbo',
                              style: TextStyle(fontWeight: FontWeight.w600),
                            ),
                          ),
                          Switch(
                            value: isTurbo,
                            onChanged: busy
                                ? null
                                : (value) {
                                    setState(() {
                                      isTurbo = value;
                                    });
                                  },
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              );
            },
          ),
          const SizedBox(height: 20),
          FilledButton.icon(
            onPressed: busy ? null : analyzeCalibrationFiles,
            icon: loadingCalibrationAnalyze
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2.3),
                  )
                : const Icon(Icons.analytics_rounded),
            label: const Text('Analyze calibration'),
          ),
        ],
      ),
    );
  }

  Widget buildResultCard() {
    final summary = asStringMap(calibrationResult?['summary']);
    final binaryDiff = asStringMap(calibrationResult?['binary_diff']);
    final maps = asList(calibrationResult?['maps']);
    final recommendations = asList(calibrationResult?['recommendations']);
    final warnings = asList(calibrationResult?['warnings']);
    final report = asStringMap(calibrationResult?['report']);
    final hasResult =
        calibrationResult != null ||
        stage1GainPercent != null ||
        potentialClass != null ||
        estimatedHpAfterStage1 != null ||
        recommendations.isNotEmpty;

    if (errorMessage != null) {
      return _SectionPanel(
        icon: Icons.error_outline_rounded,
        title: 'A aparut o eroare',
        subtitle: 'Verifica backend-ul si valorile introduse.',
        accentColor: Colors.red,
        child: Text(
          errorMessage!,
          style: const TextStyle(
            color: Color(0xFFB42318),
            fontWeight: FontWeight.w600,
          ),
        ),
      );
    }
    if (calibrationError != null) {
      return _SectionPanel(
        icon: Icons.error_outline_rounded,
        title: 'Analiza nu a putut rula',
        subtitle: 'Verifica fisierele incarcate si incearca din nou.',
        accentColor: Colors.red,
        child: Text(
          calibrationError!,
          style: const TextStyle(
            color: Color(0xFFB42318),
            fontWeight: FontWeight.w600,
          ),
        ),
      );
    }

    if (!hasResult) {
      return _SectionPanel(
        icon: Icons.auto_graph_rounded,
        title: 'Rezultat analiza',
        subtitle: 'Rezultatele vor aparea aici dupa prima analiza.',
        child: const _EmptyState(
          icon: Icons.insights_rounded,
          text:
              'Incarca originalul, fisierul tuned si apasa Analyze calibration.',
        ),
      );
    }

    return _SectionPanel(
      icon: Icons.auto_graph_rounded,
      title: 'Rezultat analiza',
      subtitle: 'Diferente, harti afectate si recomandari pentru tuner.',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (summary != null)
            LayoutBuilder(
              builder: (context, constraints) {
                final isWide = constraints.maxWidth >= 760;
                final tileWidth = isWide
                    ? (constraints.maxWidth - 28) / 3
                    : constraints.maxWidth;
                return Wrap(
                  spacing: 14,
                  runSpacing: 14,
                  children: [
                    SizedBox(
                      width: tileWidth,
                      child: _CompactMetric(
                        icon: Icons.memory_rounded,
                        label: 'Original',
                        value: formatFileSize(summary['original_size'] as int?),
                      ),
                    ),
                    SizedBox(
                      width: tileWidth,
                      child: _CompactMetric(
                        icon: Icons.table_chart_rounded,
                        label: 'Maps extracted',
                        value: '${summary['maps_extracted'] ?? 0}',
                      ),
                    ),
                    SizedBox(
                      width: tileWidth,
                      child: _CompactMetric(
                        icon: Icons.difference_rounded,
                        label: 'Maps changed',
                        value: '${summary['maps_changed'] ?? 0}',
                      ),
                    ),
                  ],
                );
              },
            ),
          if (binaryDiff != null) ...[
            const SizedBox(height: 14),
            _InlineNotice(
              icon: Icons.data_object_rounded,
              text:
                  'Binary diff: ${binaryDiff['changed_bytes']} bytes changed (${binaryDiff['changed_percent']}%).',
              color: const Color(0xFF0F766E),
            ),
          ],
          if (stage1GainPercent != null ||
              potentialClass != null ||
              estimatedHpAfterStage1 != null) ...[
            const SizedBox(height: 14),
            LayoutBuilder(
              builder: (context, constraints) {
                final isWide = constraints.maxWidth >= 680;
                final tileWidth = isWide
                    ? (constraints.maxWidth - 28) / 3
                    : constraints.maxWidth;
                return Wrap(
                  spacing: 14,
                  runSpacing: 14,
                  children: [
                    SizedBox(
                      width: tileWidth,
                      child: _MetricTile(
                        icon: Icons.trending_up_rounded,
                        label: 'Rough gain',
                        value: stage1GainPercent != null
                            ? '${stage1GainPercent!.toStringAsFixed(2)}%'
                            : '-',
                      ),
                    ),
                    SizedBox(
                      width: tileWidth,
                      child: _MetricTile(
                        icon: Icons.workspace_premium_rounded,
                        label: 'Potential',
                        value: potentialClass ?? '-',
                      ),
                    ),
                    SizedBox(
                      width: tileWidth,
                      child: _MetricTile(
                        icon: Icons.bolt_rounded,
                        label: 'Estimated HP',
                        value: estimatedHpAfterStage1 != null
                            ? estimatedHpAfterStage1!.toStringAsFixed(2)
                            : '-',
                      ),
                    ),
                  ],
                );
              },
            ),
          ],
          if (derivedFeatures != null && calibrationResult == null) ...[
            const SizedBox(height: 14),
            _DerivedMapSummary(features: derivedFeatures!),
          ],
          if (report != null) ...[
            const SizedBox(height: 14),
            _CalibrationReportPanel(report: report),
          ],
          if (recommendations.isNotEmpty) ...[
            const SizedBox(height: 14),
            _RecommendationPanel(items: recommendations),
          ],
          if (warnings.isNotEmpty) ...[
            const SizedBox(height: 14),
            for (final warning in warnings.take(3))
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: _InlineNotice(
                  icon: Icons.info_outline_rounded,
                  text: '$warning',
                  color: const Color(0xFF92400E),
                ),
              ),
          ],
          if (maps.isNotEmpty) ...[
            const SizedBox(height: 6),
            _MapBrowser(items: maps),
          ],
          if (savedPdfPath != null) ...[
            const SizedBox(height: 14),
            _PathNote(path: savedPdfPath!),
          ],
        ],
      ),
    );
  }

  Widget buildFuelMapPreviewCard() {
    if (fuelMapResult == null) {
      return const SizedBox.shrink();
    }

    final fuelMap = fuelMapResult!['fuel_map'];
    final fuelMapDerived = asStringMap(fuelMapResult!['derived_features']);

    return _SectionPanel(
      icon: Icons.table_chart_rounded,
      title: 'Fuel Map Preview',
      subtitle: 'Date generate pentru vizualizare si raport.',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              _StatusChip(
                icon: Icons.workspace_premium_rounded,
                label: 'Potential: ${fuelMapResult!['potential_class']}',
              ),
              if (fuelMapDerived != null)
                _StatusChip(
                  icon: Icons.grid_4x4_rounded,
                  label:
                      'Map: ${fuelMapDerived['rows']}x${fuelMapDerived['columns']}',
                ),
              const _StatusChip(
                icon: Icons.check_circle_rounded,
                label: 'Fuel map generat',
              ),
            ],
          ),
          const SizedBox(height: 14),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFFF8FAFC),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFFE2E8F0)),
            ),
            child: Text(
              fuelMap.toString(),
              maxLines: 8,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                fontFamily: 'monospace',
                fontSize: 12.5,
                height: 1.35,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget buildActionButton({
    required String label,
    required IconData icon,
    required Future<void> Function() onPressed,
    required bool isLoading,
  }) {
    return OutlinedButton.icon(
      onPressed: isLoading ? null : onPressed,
      icon: isLoading
          ? const SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(strokeWidth: 2.2),
            )
          : Icon(icon),
      label: Text(label),
    );
  }

  Widget buildActions() {
    return _SectionPanel(
      icon: Icons.file_download_done_rounded,
      title: 'Output',
      subtitle: 'Exporta raportul PDF pentru analiza calibrarii.',
      child: Wrap(
        spacing: 10,
        runSpacing: 10,
        children: [
          buildActionButton(
            label: 'Export PDF Report',
            icon: Icons.picture_as_pdf_rounded,
            onPressed: generatePdfReport,
            isLoading: loadingReport,
          ),
        ],
      ),
    );
  }

  Widget buildMobileStatusStrip() {
    final diff = asStringMap(calibrationResult?['binary_diff']);
    final summary = asStringMap(calibrationResult?['summary']);
    final changedValue = diff == null ? '--' : '${diff['changed_percent']}%';
    final mapsValue = summary == null ? '--' : '${summary['maps_extracted']}';
    final recValue = calibrationResult == null
        ? 'Pending'
        : '${asList(calibrationResult?['recommendations']).length}';

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          _MobileStatChip(
            icon: Icons.trending_up_rounded,
            label: 'Diff',
            value: changedValue,
          ),
          const SizedBox(width: 10),
          _MobileStatChip(
            icon: Icons.table_chart_rounded,
            label: 'Maps',
            value: mapsValue,
          ),
          const SizedBox(width: 10),
          _MobileStatChip(
            icon: Icons.tips_and_updates_rounded,
            label: 'Recs',
            value: recValue,
          ),
        ],
      ),
    );
  }

  Widget buildMobileTabContent(bool busy) {
    switch (mobileTabIndex) {
      case 1:
        return buildResultCard();
      case 2:
        return buildActions();
      default:
        return buildInputForm(busy);
    }
  }

  Widget buildMobileScaffold(bool busy) {
    return Scaffold(
      body: CustomScrollView(
        keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
        slivers: [
          SliverAppBar(
            pinned: true,
            expandedHeight: 178,
            backgroundColor: const Color(0xFF0F172A),
            foregroundColor: Colors.white,
            title: const Text(
              'ECU AI',
              style: TextStyle(fontWeight: FontWeight.w800),
            ),
            flexibleSpace: FlexibleSpaceBar(
              background: Container(
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    colors: [Color(0xFF0B1220), Color(0xFF1E3A8A)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                ),
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    if (constraints.maxHeight < 158) {
                      return const SizedBox.shrink();
                    }

                    return SafeArea(
                      child: Padding(
                        padding: const EdgeInsets.fromLTRB(18, 58, 18, 14),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            const Expanded(
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.end,
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'ECU Stage 1 Assistant',
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: TextStyle(
                                      color: Colors.white,
                                      fontSize: 22,
                                      fontWeight: FontWeight.w900,
                                      shadows: [
                                        Shadow(
                                          color: Color(0x66000000),
                                          blurRadius: 10,
                                          offset: Offset(0, 2),
                                        ),
                                      ],
                                    ),
                                  ),
                                  SizedBox(height: 6),
                                  Text(
                                    'Import fisier, estimare si sugestii tuning.',
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                    style: TextStyle(
                                      color: Colors.white70,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(width: 12),
                            const Icon(
                              Icons.memory_rounded,
                              size: 44,
                              color: Colors.white30,
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),
            ),
          ),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.only(top: 14),
              child: buildMobileStatusStrip(),
            ),
          ),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(14, 14, 14, 24),
              child: buildMobileTabContent(busy),
            ),
          ),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: mobileTabIndex,
        onDestinationSelected: (index) {
          setState(() {
            mobileTabIndex = index;
          });
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.tune_rounded),
            selectedIcon: Icon(Icons.tune),
            label: 'Date',
          ),
          NavigationDestination(
            icon: Icon(Icons.auto_graph_rounded),
            selectedIcon: Icon(Icons.auto_graph),
            label: 'Rezultat',
          ),
          NavigationDestination(
            icon: Icon(Icons.file_download_done_rounded),
            selectedIcon: Icon(Icons.file_download_done),
            label: 'Output',
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final busy =
        loadingParse ||
        loadingCalibrationAnalyze ||
        loadingAnalyze ||
        loadingFuelMap ||
        loadingReport;
    final isMobile = MediaQuery.sizeOf(context).width < _mobileBreakpoint;

    if (isMobile) {
      return buildMobileScaffold(busy);
    }

    return Scaffold(
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            pinned: true,
            expandedHeight: 168,
            backgroundColor: const Color(0xFF111827),
            foregroundColor: Colors.white,
            flexibleSpace: FlexibleSpaceBar(
              titlePadding: const EdgeInsetsDirectional.only(
                start: 24,
                bottom: 18,
              ),
              title: const Text(
                'ECU Stage 1 Assistant',
                style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w900,
                  shadows: [
                    Shadow(
                      color: Color(0x7A000000),
                      blurRadius: 12,
                      offset: Offset(0, 2),
                    ),
                  ],
                ),
              ),
              background: Container(
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    colors: [Color(0xFF0B1220), Color(0xFF1E3A8A)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                ),
                child: Align(
                  alignment: Alignment.bottomRight,
                  child: Padding(
                    padding: EdgeInsets.fromLTRB(24, 24, 24, 26),
                    child: Icon(
                      Icons.memory_rounded,
                      size: 74,
                      color: Colors.white24,
                    ),
                  ),
                ),
              ),
            ),
          ),
          SliverToBoxAdapter(
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 1080),
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(20, 22, 20, 32),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const _IntroBand(),
                      const SizedBox(height: 18),
                      buildInputForm(busy),
                      const SizedBox(height: 18),
                      buildResultCard(),
                      const SizedBox(height: 18),
                      buildActions(),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _IntroBand extends StatelessWidget {
  const _IntroBand();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFE2E8F0)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x0F0F172A),
            blurRadius: 22,
            offset: Offset(0, 10),
          ),
        ],
      ),
      child: Wrap(
        spacing: 16,
        runSpacing: 14,
        crossAxisAlignment: WrapCrossAlignment.center,
        alignment: WrapAlignment.spaceBetween,
        children: [
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 640),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'ECU Stage 1 Assistant',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w800,
                    color: const Color(0xFF0F172A),
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  'Incarca un fisier ECU sau o harta exportata, apoi primeste estimare si sugestii explicabile.',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: const Color(0xFF475569),
                    height: 1.45,
                  ),
                ),
              ],
            ),
          ),
          const _StatusPill(
            icon: Icons.api_rounded,
            label: 'API local: 127.0.0.1:8000',
          ),
        ],
      ),
    );
  }
}

class _InlineNotice extends StatelessWidget {
  final IconData icon;
  final String text;
  final Color color;

  const _InlineNotice({
    required this.icon,
    required this.text,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.24)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              text,
              style: TextStyle(color: color, fontWeight: FontWeight.w700),
            ),
          ),
        ],
      ),
    );
  }
}

class _CompactMetric extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _CompactMetric({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 78,
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Row(
        children: [
          Icon(icon, color: const Color(0xFF0F766E)),
          const SizedBox(width: 11),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  value,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Color(0xFF0F172A),
                    fontWeight: FontWeight.w900,
                    fontSize: 18,
                  ),
                ),
                Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Color(0xFF64748B),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _RecommendationPanel extends StatelessWidget {
  final List<dynamic> items;

  const _RecommendationPanel({required this.items});

  @override
  Widget build(BuildContext context) {
    final recommendations = items
        .map((item) => Map<String, dynamic>.from(item as Map))
        .take(6)
        .toList();

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              const Icon(Icons.tips_and_updates_rounded, size: 20),
              const SizedBox(width: 9),
              Expanded(
                child: Text(
                  'Power Improvement Suggestions',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          for (final recommendation in recommendations) ...[
            _RecommendationTile(item: recommendation),
            if (recommendation != recommendations.last)
              const SizedBox(height: 10),
          ],
        ],
      ),
    );
  }
}

class _RecommendationTile extends StatelessWidget {
  final Map<String, dynamic> item;

  const _RecommendationTile({required this.item});

  Color get accent {
    switch (item['risk']) {
      case 'high':
      case 'medium-high':
        return const Color(0xFFB45309);
      case 'unknown':
        return const Color(0xFF64748B);
      default:
        return const Color(0xFF0F766E);
    }
  }

  @override
  Widget build(BuildContext context) {
    final maps = item['maps'] is List ? (item['maps'] as List) : const [];
    final observations = item['observations'] is List
        ? (item['observations'] as List)
        : const [];
    final actions = item['actions'] is List
        ? (item['actions'] as List)
        : const [];
    final benefits = item['benefits'] is List
        ? (item['benefits'] as List)
        : const [];
    final risks = item['risks'] is List ? (item['risks'] as List) : const [];
    final checks = item['checks'] is List ? (item['checks'] as List) : const [];

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: accent.withValues(alpha: 0.24)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(Icons.auto_fix_high_rounded, color: accent, size: 20),
              const SizedBox(width: 9),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      item['title']?.toString() ?? 'Suggestion',
                      style: const TextStyle(
                        color: Color(0xFF0F172A),
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      item['reason']?.toString() ?? '-',
                      style: const TextStyle(
                        color: Color(0xFF475569),
                        height: 1.35,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _StatusChip(
                icon: Icons.trending_up_rounded,
                label: '${item['suggested_change']}',
              ),
              if (item['mode_label'] != null)
                _StatusChip(
                  icon: Icons.route_rounded,
                  label: '${item['mode_label']}',
                ),
              if (item['priority'] != null)
                _StatusChip(
                  icon: Icons.priority_high_rounded,
                  label: 'Priority: ${item['priority']}',
                ),
              if (item['benefit_level'] != null)
                _StatusChip(
                  icon: Icons.bolt_rounded,
                  label: 'Benefit: ${item['benefit_level']}',
                ),
              _StatusChip(
                icon: Icons.location_searching_rounded,
                label: '${item['target_zone']}',
              ),
              _StatusChip(
                icon: Icons.health_and_safety_rounded,
                label: 'Risk: ${item['risk']}',
              ),
              _StatusChip(
                icon: Icons.verified_rounded,
                label: 'Confidence: ${item['confidence']}',
              ),
            ],
          ),
          if (observations.isNotEmpty) ...[
            const SizedBox(height: 10),
            _RecommendationSection(
              title: 'Observatii',
              icon: Icons.visibility_rounded,
              items: observations,
              color: const Color(0xFF2563EB),
            ),
          ],
          if (actions.isNotEmpty) ...[
            const SizedBox(height: 8),
            _RecommendationSection(
              title: 'Actiuni recomandate',
              icon: Icons.build_circle_rounded,
              items: actions,
              color: const Color(0xFF0F766E),
            ),
          ],
          if (benefits.isNotEmpty || risks.isNotEmpty) ...[
            const SizedBox(height: 8),
            LayoutBuilder(
              builder: (context, constraints) {
                final isWide = constraints.maxWidth >= 620;
                return Wrap(
                  spacing: 10,
                  runSpacing: 8,
                  children: [
                    if (benefits.isNotEmpty)
                      SizedBox(
                        width: isWide
                            ? (constraints.maxWidth - 10) / 2
                            : constraints.maxWidth,
                        child: _RecommendationSection(
                          title: 'Beneficii',
                          icon: Icons.add_chart_rounded,
                          items: benefits,
                          color: const Color(0xFF0F766E),
                          maxItems: 2,
                        ),
                      ),
                    if (risks.isNotEmpty)
                      SizedBox(
                        width: isWide
                            ? (constraints.maxWidth - 10) / 2
                            : constraints.maxWidth,
                        child: _RecommendationSection(
                          title: 'Riscuri',
                          icon: Icons.warning_amber_rounded,
                          items: risks,
                          color: const Color(0xFFB45309),
                          maxItems: 2,
                        ),
                      ),
                  ],
                );
              },
            ),
          ],
          if (maps.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              'Maps: ${maps.take(4).join(', ')}',
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: Color(0xFF334155),
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
          if (checks.isNotEmpty) ...[
            const SizedBox(height: 8),
            _AlignedBulletList(
              items: checks.take(3).toList(),
              color: const Color(0xFF0F766E),
              icon: Icons.check_rounded,
            ),
          ],
        ],
      ),
    );
  }
}

class _RecommendationSection extends StatelessWidget {
  final String title;
  final IconData icon;
  final List<dynamic> items;
  final Color color;
  final int maxItems;

  const _RecommendationSection({
    required this.title,
    required this.icon,
    required this.items,
    required this.color,
    this.maxItems = 3,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.045),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withValues(alpha: 0.13)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 17, color: color),
              const SizedBox(width: 7),
              Text(
                title,
                style: TextStyle(color: color, fontWeight: FontWeight.w900),
              ),
            ],
          ),
          const SizedBox(height: 6),
          _AlignedBulletList(
            items: items.take(maxItems).toList(),
            color: color,
            icon: Icons.circle,
            compact: true,
          ),
        ],
      ),
    );
  }
}

class _AlignedBulletList extends StatelessWidget {
  final List<dynamic> items;
  final Color color;
  final IconData icon;
  final bool compact;

  const _AlignedBulletList({
    required this.items,
    required this.color,
    this.icon = Icons.circle,
    this.compact = false,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final item in items)
          Padding(
            padding: EdgeInsets.only(bottom: compact ? 3 : 6),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SizedBox(
                  width: 18,
                  height: 20,
                  child: Align(
                    alignment: const Alignment(0, -0.15),
                    child: Icon(
                      icon,
                      size: icon == Icons.circle ? 6 : 16,
                      color: color,
                    ),
                  ),
                ),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(
                    '$item',
                    style: const TextStyle(
                      color: Color(0xFF475569),
                      height: 1.35,
                    ),
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _CalibrationReportPanel extends StatelessWidget {
  final Map<String, dynamic> report;

  const _CalibrationReportPanel({required this.report});

  List<dynamic> _list(String key) {
    final value = report[key];
    return value is List ? value : const [];
  }

  @override
  Widget build(BuildContext context) {
    final topChanges = _list('top_changes');
    final checks = _list('validation_checks');
    final tunerSummary = _list('tuner_summary');

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.assignment_rounded, color: Color(0xFF0F766E)),
              const SizedBox(width: 9),
              Expanded(
                child: Text(
                  'Tuner Report',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            report['headline']?.toString() ?? 'Analiza calibrarii este gata.',
            style: const TextStyle(
              color: Color(0xFF334155),
              fontWeight: FontWeight.w700,
            ),
          ),
          if (tunerSummary.isNotEmpty) ...[
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFEFF6FF),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFFBFDBFE)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(
                        Icons.summarize_rounded,
                        size: 18,
                        color: Color(0xFF1D4ED8),
                      ),
                      SizedBox(width: 7),
                      Text(
                        'Tuner summary',
                        style: TextStyle(
                          color: Color(0xFF1D4ED8),
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 7),
                  _AlignedBulletList(
                    items: tunerSummary.take(4).toList(),
                    color: const Color(0xFF1D4ED8),
                    icon: Icons.circle,
                    compact: true,
                  ),
                ],
              ),
            ),
          ],
          if (topChanges.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(
              'Top modified maps',
              style: Theme.of(
                context,
              ).textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 8),
            for (final change in topChanges.take(4))
              _ReportChangeRow(
                change: Map<String, dynamic>.from(change as Map),
              ),
          ],
          if (checks.isNotEmpty) ...[
            const SizedBox(height: 12),
            _AlignedBulletList(
              items: checks.take(5).toList(),
              color: const Color(0xFF0F766E),
              icon: Icons.check_circle_rounded,
            ),
          ],
        ],
      ),
    );
  }
}

class _ReportChangeRow extends StatelessWidget {
  final Map<String, dynamic> change;

  const _ReportChangeRow({required this.change});

  @override
  Widget build(BuildContext context) {
    final zone = change['zone_text']?.toString();
    final unit = change['unit']?.toString();
    final delta = change['max_abs_delta'];
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Row(
        children: [
          const Icon(Icons.difference_rounded, color: Color(0xFF0F766E)),
          const SizedBox(width: 9),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  change['name']?.toString() ?? 'Map',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w900),
                ),
                Text(
                  [
                    change['category'],
                    if (zone != null && zone.isNotEmpty) zone,
                    'max delta $delta${unit == null || unit.isEmpty ? '' : ' $unit'}',
                  ].where((item) => item != null && '$item'.isNotEmpty).join(' | '),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Color(0xFF64748B),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
          Text(
            '${change['changed_percent'] ?? 0}%',
            style: const TextStyle(
              color: Color(0xFF0F766E),
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}

class _MapBrowser extends StatefulWidget {
  final List<dynamic> items;

  const _MapBrowser({required this.items});

  @override
  State<_MapBrowser> createState() => _MapBrowserState();
}

class _MapBrowserState extends State<_MapBrowser> {
  final searchController = TextEditingController();
  String categoryFilter = 'all';
  String sortMode = 'changed';
  bool changedOnly = false;

  @override
  void dispose() {
    searchController.dispose();
    super.dispose();
  }

  List<Map<String, dynamic>> get allMaps {
    return widget.items
        .map((item) => Map<String, dynamic>.from(item as Map))
        .toList();
  }

  int changedCells(Map<String, dynamic> item) {
    final diff = Map<String, dynamic>.from((item['diff'] as Map?) ?? {});
    return ((diff['changed_cells'] as num?) ?? 0).toInt();
  }

  List<String> get categories {
    final values = allMaps
        .map((item) => item['category']?.toString() ?? 'unknown')
        .toSet()
        .toList();
    values.sort();
    return values;
  }

  bool matchesSearch(Map<String, dynamic> item, String query) {
    if (query.isEmpty) return true;
    final haystack = [
      item['name'],
      item['short_name'],
      item['category'],
      item['address_hex'],
      item['data_type'],
    ].whereType<Object>().join(' ').toLowerCase();
    return haystack.contains(query);
  }

  List<Map<String, dynamic>> get visibleItems {
    final validCategory = categories.contains(categoryFilter)
        ? categoryFilter
        : 'all';
    final query = searchController.text.trim().toLowerCase();
    final maps = allMaps.where((item) {
      final category = item['category']?.toString() ?? 'unknown';
      if (validCategory != 'all' && category != validCategory) return false;
      if (changedOnly && changedCells(item) == 0) return false;
      return matchesSearch(item, query);
    }).toList();

    maps.sort((left, right) {
      if (sortMode == 'name') {
        return (left['name']?.toString() ?? '').compareTo(
          right['name']?.toString() ?? '',
        );
      }
      if (sortMode == 'category') {
        final categoryCompare = (left['category']?.toString() ?? '').compareTo(
          right['category']?.toString() ?? '',
        );
        if (categoryCompare != 0) return categoryCompare;
      }
      return changedCells(right).compareTo(changedCells(left));
    });
    return maps;
  }

  @override
  Widget build(BuildContext context) {
    final totalMaps = allMaps.length;
    final maps = visibleItems;
    final categoryItems = ['all', ...categories];
    final selectedCategory = categoryItems.contains(categoryFilter)
        ? categoryFilter
        : 'all';

    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          initiallyExpanded: false,
          tilePadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
          childrenPadding: EdgeInsets.zero,
          leading: const Icon(Icons.view_list_rounded, size: 20),
          title: Text(
            'Map Browser',
            style: Theme.of(
              context,
            ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w900),
          ),
          subtitle: Text(
            'Cautare, filtre si preview 3D pentru hartile extrase.',
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: const Color(0xFF64748B),
              fontWeight: FontWeight.w600,
            ),
          ),
          trailing: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                '${maps.length}/$totalMaps maps',
                style: const TextStyle(
                  color: Color(0xFF64748B),
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(width: 8),
              const Icon(Icons.expand_more_rounded),
            ],
          ),
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 4, 14, 10),
              child: Wrap(
                spacing: 10,
                runSpacing: 10,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  SizedBox(
                    width: 300,
                    child: TextField(
                      controller: searchController,
                      onChanged: (_) => setState(() {}),
                      decoration: const InputDecoration(
                        prefixIcon: Icon(Icons.search_rounded),
                        labelText: 'Search maps',
                        hintText: 'name, address, category',
                      ),
                    ),
                  ),
                  SizedBox(
                    width: 220,
                    child: DropdownButtonFormField<String>(
                      initialValue: selectedCategory,
                      decoration: const InputDecoration(
                        prefixIcon: Icon(Icons.category_rounded),
                        labelText: 'Category',
                      ),
                      items: [
                        for (final category in categoryItems)
                          DropdownMenuItem(
                            value: category,
                            child: Text(
                              category == 'all' ? 'All categories' : category,
                            ),
                          ),
                      ],
                      onChanged: (value) {
                        if (value == null) return;
                        setState(() {
                          categoryFilter = value;
                        });
                      },
                    ),
                  ),
                  SizedBox(
                    width: 190,
                    child: DropdownButtonFormField<String>(
                      initialValue: sortMode,
                      decoration: const InputDecoration(
                        prefixIcon: Icon(Icons.sort_rounded),
                        labelText: 'Sort',
                      ),
                      items: const [
                        DropdownMenuItem(
                          value: 'changed',
                          child: Text('Most changed'),
                        ),
                        DropdownMenuItem(
                          value: 'category',
                          child: Text('Category'),
                        ),
                        DropdownMenuItem(value: 'name', child: Text('Name')),
                      ],
                      onChanged: (value) {
                        if (value == null) return;
                        setState(() {
                          sortMode = value;
                        });
                      },
                    ),
                  ),
                  FilterChip(
                    selected: changedOnly,
                    avatar: const Icon(Icons.difference_rounded, size: 18),
                    label: const Text('Changed only'),
                    onSelected: (value) {
                      setState(() {
                        changedOnly = value;
                      });
                    },
                  ),
                ],
              ),
            ),
            if (maps.isEmpty)
              const Padding(
                padding: EdgeInsets.fromLTRB(14, 0, 14, 14),
                child: _EmptyState(
                  icon: Icons.manage_search_rounded,
                  text: 'Nu exista harti pentru filtrele selectate.',
                ),
              )
            else
              for (final item in maps.take(40)) _MapBrowserTile(item: item),
            if (maps.length > 40)
              Padding(
                padding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
                child: Text(
                  'Afisate primele 40 rezultate. Foloseste cautarea sau filtrele pentru focus.',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: const Color(0xFF64748B),
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _MapBrowserTile extends StatelessWidget {
  final Map<String, dynamic> item;

  const _MapBrowserTile({required this.item});

  @override
  Widget build(BuildContext context) {
    final diff = Map<String, dynamic>.from((item['diff'] as Map?) ?? {});
    final changedCells = ((diff['changed_cells'] as num?) ?? 0).toInt();
    final changedPercent = diff['changed_percent'] ?? 0;
    final hasModified = item['modified_preview'] != null;
    final shortName = item['short_name']?.toString();
    final units = item['units'] is List
        ? (item['units'] as List).map((unit) => unit.toString()).join(', ')
        : '';
    final axes = item['axes'] is List ? item['axes'] as List : const [];
    final axisSummary = axes
        .take(2)
        .map((axis) {
          final axisMap = Map<String, dynamic>.from(axis as Map);
          final unit = axisMap['unit'] ?? axisMap['label'] ?? 'axis';
          final min = axisMap['min'];
          final max = axisMap['max'];
          if (min == null || max == null) return unit.toString();
          return '$unit $min-$max';
        })
        .join(' / ');
    final factor = item['factor'];
    final offset = item['offset'];
    final hasScale =
        (factor is num && (factor - 1.0).abs() > 0.0000001) ||
        (offset is num && offset.abs() > 0.0000001);
    final metadata =
        [
              item['address_hex'],
              '${item['rows']}x${item['columns']}',
              item['data_type'],
              item['category'],
              if (shortName != null && shortName.isNotEmpty) shortName,
              if (units.isNotEmpty) units,
              if (axisSummary.isNotEmpty) axisSummary,
              if (hasScale) 'scale ${factor ?? '-'}',
            ]
            .where((value) => value != null && value.toString().isNotEmpty)
            .join(' | ');

    return ExpansionTile(
      tilePadding: const EdgeInsets.symmetric(horizontal: 14),
      childrenPadding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
      leading: Icon(
        changedCells > 0 ? Icons.difference_rounded : Icons.table_rows_rounded,
        color: changedCells > 0
            ? const Color(0xFF0F766E)
            : const Color(0xFF64748B),
      ),
      title: Text(
        item['name']?.toString() ?? 'Map',
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: const TextStyle(fontWeight: FontWeight.w900),
      ),
      subtitle: Text(metadata, maxLines: 1, overflow: TextOverflow.ellipsis),
      trailing: SizedBox(
        width: 76,
        child: Text(
          hasModified ? '$changedPercent%' : 'view',
          textAlign: TextAlign.end,
          style: TextStyle(
            color: changedCells > 0
                ? const Color(0xFF0F766E)
                : const Color(0xFF64748B),
            fontWeight: FontWeight.w900,
          ),
        ),
      ),
      children: [
        _MapMetricStrip(item: item, diff: diff),
        const SizedBox(height: 10),
        _MapSurfacePreview(
          title: hasModified ? 'Modified surface' : 'Original surface',
          rows: hasModified
              ? item['modified_surface_preview'] ?? item['modified_preview']
              : item['surface_preview'] ?? item['preview'],
          deltaRows: item['delta_surface_preview'] ?? item['delta_preview'],
        ),
        const SizedBox(height: 10),
        _MapPreviewGrid(title: 'Original preview', rows: item['preview']),
        if (hasModified) ...[
          const SizedBox(height: 10),
          _MapPreviewGrid(
            title: 'Modified preview',
            rows: item['modified_preview'],
          ),
        ],
        if (item['delta_preview'] != null) ...[
          const SizedBox(height: 10),
          _MapPreviewGrid(
            title: 'Delta preview',
            rows: item['delta_preview'],
            highlightDelta: true,
          ),
        ],
      ],
    );
  }
}

class _MapMetricStrip extends StatelessWidget {
  final Map<String, dynamic> item;
  final Map<String, dynamic> diff;

  const _MapMetricStrip({required this.item, required this.diff});

  @override
  Widget build(BuildContext context) {
    final summary = Map<String, dynamic>.from((item['summary'] as Map?) ?? {});
    final modifiedSummary = Map<String, dynamic>.from(
      (item['modified_summary'] as Map?) ?? {},
    );
    final axes = item['axes'] is List ? item['axes'] as List : const [];
    final affectedZone = item['affected_zone'] is List
        ? item['affected_zone'] as List
        : const [];
    final factor = item['factor'];
    final offset = item['offset'];
    final hasScale =
        (factor is num && (factor - 1.0).abs() > 0.0000001) ||
        (offset is num && offset.abs() > 0.0000001);
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        _StatusChip(
          icon: Icons.memory_rounded,
          label: '${item['address_hex']} / ${item['bytes']} bytes',
        ),
        _StatusChip(
          icon: Icons.analytics_rounded,
          label: 'Orig mean: ${summary['mean'] ?? '-'}',
        ),
        if (hasScale)
          _StatusChip(
            icon: Icons.straighten_rounded,
            label: 'Scale: x${factor ?? '-'} + ${offset ?? 0}',
          ),
        for (final axis in axes.take(3))
          _StatusChip(
            icon: Icons.timeline_rounded,
            label: _axisChipLabel(Map<String, dynamic>.from(axis as Map)),
          ),
        for (final zone in affectedZone.take(3))
          _StatusChip(
            icon: Icons.my_location_rounded,
            label: _zoneChipLabel(Map<String, dynamic>.from(zone as Map)),
          ),
        if (modifiedSummary.isNotEmpty)
          _StatusChip(
            icon: Icons.compare_arrows_rounded,
            label: 'Mod mean: ${modifiedSummary['mean'] ?? '-'}',
          ),
        if (diff.isNotEmpty)
          _StatusChip(
            icon: Icons.functions_rounded,
            label: 'Delta max: ${diff['max_abs_delta'] ?? '-'}',
          ),
      ],
    );
  }

  String _axisChipLabel(Map<String, dynamic> axis) {
    final unit = axis['unit'] ?? axis['label'] ?? 'Axis';
    final min = axis['min'];
    final max = axis['max'];
    final byteOrder = axis['resolved_byte_order'];
    if (min == null || max == null) {
      return '$unit';
    }
    return '$unit: $min-$max${byteOrder == null ? '' : ' $byteOrder'}';
  }

  String _zoneChipLabel(Map<String, dynamic> zone) {
    final label = zone['label'] ?? 'Zone';
    final min = zone['min'];
    final max = zone['max'];
    if (min == null || max == null) {
      return '$label changed';
    }
    return '$label changed: $min-$max';
  }
}

class _MapPreviewGrid extends StatelessWidget {
  final String title;
  final dynamic rows;
  final bool highlightDelta;

  const _MapPreviewGrid({
    required this.title,
    required this.rows,
    this.highlightDelta = false,
  });

  @override
  Widget build(BuildContext context) {
    final tableRows = rows is List ? rows!.cast<dynamic>() : <dynamic>[];
    var columnCount = 0;
    for (final row in tableRows) {
      if (row is List && row.length > columnCount) {
        columnCount = row.length;
      }
    }
    final calculatedWidth = columnCount * _MapValueCell.cellWidth;
    final gridMinWidth = calculatedWidth < 116.0 ? 116.0 : calculatedWidth;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(
            color: Color(0xFF334155),
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(height: 6),
        LayoutBuilder(
          builder: (context, constraints) {
            final viewportWidth = constraints.maxWidth.isFinite
                ? constraints.maxWidth
                : gridMinWidth;
            return ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: SizedBox(
                width: viewportWidth,
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  clipBehavior: Clip.hardEdge,
                  child: ConstrainedBox(
                    constraints: BoxConstraints(minWidth: gridMinWidth + 4),
                    child: IntrinsicWidth(
                      child: Container(
                        decoration: BoxDecoration(
                          border: Border.all(color: const Color(0xFFE2E8F0)),
                          borderRadius: BorderRadius.circular(8),
                          color: Colors.white,
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            for (final row in tableRows)
                              Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  for (final value
                                      in (row is List ? row : const []))
                                    _MapValueCell(
                                      value: value,
                                      highlightDelta: highlightDelta,
                                    ),
                                ],
                              ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            );
          },
        ),
      ],
    );
  }
}

class _MapValueCell extends StatelessWidget {
  static const double cellWidth = 76;

  final dynamic value;
  final bool highlightDelta;

  const _MapValueCell({required this.value, required this.highlightDelta});

  @override
  Widget build(BuildContext context) {
    final number = value is num ? value.toDouble() : null;
    final text = number == null
        ? '$value'
        : number.toStringAsFixed(number.abs() >= 100 ? 1 : 3);
    final color = !highlightDelta || number == null || number == 0
        ? Colors.white
        : number > 0
        ? const Color(0xFFEFF6FF)
        : const Color(0xFFFFF1F2);

    return Container(
      width: cellWidth,
      height: 34,
      alignment: Alignment.centerRight,
      padding: const EdgeInsets.symmetric(horizontal: 8),
      decoration: BoxDecoration(
        color: color,
        border: const Border(
          right: BorderSide(color: Color(0xFFE2E8F0)),
          bottom: BorderSide(color: Color(0xFFE2E8F0)),
        ),
      ),
      child: Text(
        text,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: const TextStyle(
          fontFamily: 'monospace',
          fontSize: 12,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _MobileStatChip extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _MobileStatChip({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 136,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFE2E8F0)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x0D0F172A),
            blurRadius: 16,
            offset: Offset(0, 8),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 34,
            height: 34,
            decoration: BoxDecoration(
              color: Theme.of(
                context,
              ).colorScheme.primary.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(
              icon,
              size: 19,
              color: Theme.of(context).colorScheme.primary,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  value,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Color(0xFF0F172A),
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 1),
                Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Color(0xFF64748B),
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionPanel extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final Widget child;
  final Color? accentColor;

  const _SectionPanel({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.child,
    this.accentColor,
  });

  @override
  Widget build(BuildContext context) {
    final color = accentColor ?? Theme.of(context).colorScheme.primary;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFE2E8F0)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x0D0F172A),
            blurRadius: 18,
            offset: Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, color: color),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      subtitle,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: const Color(0xFF64748B),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          child,
        ],
      ),
    );
  }
}

class _MetricTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _MetricTile({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 116,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: Theme.of(context).colorScheme.primary),
          const Spacer(),
          Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.w900,
              color: const Color(0xFF0F172A),
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: const Color(0xFF64748B),
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _DerivedMapSummary extends StatelessWidget {
  final Map<String, dynamic> features;

  const _DerivedMapSummary({required this.features});

  String _value(String key, {String suffix = ''}) {
    final value = features[key];
    if (value == null) return '-';
    if (value is num) {
      return '${value.toStringAsFixed(value % 1 == 0 ? 0 : 2)}$suffix';
    }
    return '$value$suffix';
  }

  @override
  Widget build(BuildContext context) {
    final rows = features['rows'] ?? '-';
    final columns = features['columns'] ?? '-';

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Wrap(
        spacing: 10,
        runSpacing: 10,
        children: [
          _StatusChip(
            icon: Icons.grid_on_rounded,
            label: '$rows x $columns ${_value('map_type')}',
          ),
          _StatusChip(
            icon: Icons.speed_rounded,
            label: 'RPM: ${_value('rpm')}',
          ),
          _StatusChip(
            icon: Icons.local_gas_station_rounded,
            label: 'IQ: ${_value('injection_quantity', suffix: ' mg')}',
          ),
          _StatusChip(
            icon: Icons.compress_rounded,
            label: 'Boost: ${_value('boost_pressure', suffix: ' bar')}',
          ),
          _StatusChip(icon: Icons.air_rounded, label: 'AFR: ${_value('afr')}'),
          _StatusChip(
            icon: Icons.functions_rounded,
            label: 'Range: ${_value('min_value')} .. ${_value('max_value')}',
          ),
        ],
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  final IconData icon;
  final String label;

  const _StatusPill({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFFECFDF5),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: const Color(0xFFA7F3D0)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 18, color: const Color(0xFF047857)),
          const SizedBox(width: 8),
          Text(
            label,
            style: const TextStyle(
              color: Color(0xFF065F46),
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  final IconData icon;
  final String label;

  const _StatusChip({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Chip(
      avatar: Icon(icon, size: 18),
      label: Text(label),
      side: const BorderSide(color: Color(0xFFD9E0EC)),
      backgroundColor: Colors.white,
      labelStyle: const TextStyle(fontWeight: FontWeight.w600),
    );
  }
}

class _CalibrationFilePicker extends StatefulWidget {
  final String label;
  final String? fileName;
  final IconData icon;
  final bool optional;
  final bool disabled;
  final VoidCallback onPressed;
  final VoidCallback onClear;

  const _CalibrationFilePicker({
    required this.label,
    required this.fileName,
    required this.icon,
    required this.optional,
    required this.disabled,
    required this.onPressed,
    required this.onClear,
  });

  @override
  State<_CalibrationFilePicker> createState() => _CalibrationFilePickerState();
}

class _CalibrationFilePickerState extends State<_CalibrationFilePicker> {
  bool hovered = false;

  @override
  Widget build(BuildContext context) {
    final hasFile = widget.fileName != null;
    final showClear =
        hasFile && (hovered || MediaQuery.sizeOf(context).width < 720);
    final borderColor = hasFile
        ? const Color(0xFF93C5FD)
        : const Color(0xFFD9E0EC);
    final backgroundColor = hasFile ? const Color(0xFFF8FBFF) : Colors.white;

    return MouseRegion(
      onEnter: (_) => setState(() => hovered = true),
      onExit: (_) => setState(() => hovered = false),
      child: Material(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(12),
        child: InkWell(
          onTap: widget.disabled ? null : widget.onPressed,
          borderRadius: BorderRadius.circular(12),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 150),
            height: 56,
            padding: const EdgeInsets.only(left: 14, right: 6),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: hovered && !widget.disabled
                    ? Theme.of(context).colorScheme.primary
                    : borderColor,
                width: hovered && !widget.disabled ? 1.4 : 1,
              ),
            ),
            child: Row(
              children: [
                Icon(
                  hasFile ? Icons.check_circle_rounded : widget.icon,
                  color: hasFile
                      ? const Color(0xFF0F766E)
                      : const Color(0xFF334155),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    hasFile
                        ? widget.fileName!
                        : '${widget.label}${widget.optional ? ' optional' : ''}',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: hasFile
                          ? const Color(0xFF0F172A)
                          : const Color(0xFF475569),
                      fontWeight: hasFile ? FontWeight.w800 : FontWeight.w600,
                    ),
                  ),
                ),
                if (hasFile)
                  IgnorePointer(
                    ignoring: !showClear,
                    child: AnimatedOpacity(
                      opacity: showClear ? 1 : 0,
                      duration: const Duration(milliseconds: 120),
                      child: IconButton(
                        tooltip: 'Remove file',
                        visualDensity: VisualDensity.compact,
                        onPressed: widget.disabled ? null : widget.onClear,
                        icon: const Icon(Icons.close_rounded),
                      ),
                    ),
                  )
                else
                  const Padding(
                    padding: EdgeInsets.only(right: 10),
                    child: Icon(Icons.upload_file_rounded, size: 20),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _PathNote extends StatelessWidget {
  final String path;

  const _PathNote({required this.path});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Row(
        children: [
          const Icon(Icons.picture_as_pdf_rounded, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              path,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}

class _MapSurfacePreview extends StatelessWidget {
  final String title;
  final dynamic rows;
  final dynamic deltaRows;

  const _MapSurfacePreview({
    required this.title,
    required this.rows,
    this.deltaRows,
  });

  List<List<double>> _matrix(dynamic value) {
    if (value is! List) return const [];
    return value
        .whereType<List>()
        .map(
          (row) => row
              .map((cell) => cell is num ? cell.toDouble() : double.nan)
              .where((cell) => cell.isFinite)
              .toList(),
        )
        .where((row) => row.isNotEmpty)
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    final matrix = _matrix(rows);
    final deltaMatrix = _matrix(deltaRows);
    if (matrix.length < 2 || matrix.first.length < 2) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(Icons.terrain_rounded, size: 18),
            const SizedBox(width: 7),
            Text(
              title,
              style: const TextStyle(
                fontWeight: FontWeight.w900,
                color: Color(0xFF334155),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Container(
          height: 230,
          width: double.infinity,
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFFE2E8F0)),
          ),
          child: Stack(
            children: [
              Positioned.fill(
                child: CustomPaint(
                  painter: _SurfacePainter(
                    matrix: matrix,
                    deltaMatrix: deltaMatrix,
                  ),
                ),
              ),
              const Positioned(left: 12, bottom: 10, child: _SurfaceLegend()),
            ],
          ),
        ),
      ],
    );
  }
}

class _SurfaceLegend extends StatelessWidget {
  const _SurfaceLegend();

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.88),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'Low',
              style: TextStyle(
                color: Color(0xFF64748B),
                fontSize: 11,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(width: 6),
            Container(
              width: 78,
              height: 8,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(999),
                gradient: const LinearGradient(
                  colors: [
                    Color(0xFF38BDF8),
                    Color(0xFFFACC15),
                    Color(0xFFDC2626),
                  ],
                ),
              ),
            ),
            const SizedBox(width: 6),
            const Text(
              'Peak',
              style: TextStyle(
                color: Color(0xFF64748B),
                fontSize: 11,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SurfacePainter extends CustomPainter {
  final List<List<double>> matrix;
  final List<List<double>> deltaMatrix;

  const _SurfacePainter({required this.matrix, required this.deltaMatrix});

  @override
  void paint(Canvas canvas, Size size) {
    final rows = matrix.length;
    final columns = matrix
        .map((row) => row.length)
        .reduce((a, b) => a < b ? a : b);
    if (rows < 2 || columns < 2) return;

    final values = <double>[
      for (final row in matrix)
        for (final value in row.take(columns)) value,
    ]..sort();
    final lowIndex = (values.length * 0.05).floor().clamp(0, values.length - 1);
    final highIndex = (values.length * 0.95).floor().clamp(
      0,
      values.length - 1,
    );
    final lowValue = values[lowIndex];
    final highValue = values[highIndex];
    final span = (highValue - lowValue).abs() < 0.000001
        ? 1.0
        : highValue - lowValue;
    final zHeight = (rows + columns) * 0.46;

    double normalizedValue(int row, int column) {
      final raw = (matrix[row][column] - lowValue) / span;
      return raw.clamp(0.0, 1.0);
    }

    Offset logicalProject(int row, int column) {
      final normalized = normalizedValue(row, column);
      return Offset(
        (column - row).toDouble(),
        (column + row) * 0.52 - normalized * zHeight,
      );
    }

    final logical = List.generate(
      rows,
      (row) => List.generate(columns, (column) => logicalProject(row, column)),
    );
    var minX = logical.first.first.dx;
    var maxX = logical.first.first.dx;
    var minY = logical.first.first.dy;
    var maxY = logical.first.first.dy;
    for (final row in logical) {
      for (final point in row) {
        if (point.dx < minX) minX = point.dx;
        if (point.dx > maxX) maxX = point.dx;
        if (point.dy < minY) minY = point.dy;
        if (point.dy > maxY) maxY = point.dy;
      }
    }

    const padding = 18.0;
    final logicalWidth = (maxX - minX).abs() < 0.000001 ? 1.0 : maxX - minX;
    final logicalHeight = (maxY - minY).abs() < 0.000001 ? 1.0 : maxY - minY;
    final scaleX = (size.width - padding * 2) / logicalWidth;
    final scaleY = (size.height - padding * 2) / logicalHeight;
    final scale = scaleX < scaleY ? scaleX : scaleY;
    final drawnWidth = logicalWidth * scale;
    final drawnHeight = logicalHeight * scale;
    final offset = Offset(
      (size.width - drawnWidth) / 2 - minX * scale,
      (size.height - drawnHeight) / 2 - minY * scale,
    );

    Offset project(int row, int column) {
      final point = logical[row][column];
      return Offset(point.dx * scale + offset.dx, point.dy * scale + offset.dy);
    }

    final gridPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 0.65
      ..color = const Color(0x4D334155);
    final fillPaint = Paint()..style = PaintingStyle.fill;
    final highlightPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.6
      ..color = const Color(0xFF0F766E);
    final shadowPaint = Paint()
      ..style = PaintingStyle.fill
      ..color = const Color(0x110F172A);

    final shadow = Path()
      ..moveTo(project(rows - 1, 0).dx, size.height - padding)
      ..lineTo(project(rows - 1, columns - 1).dx, size.height - padding)
      ..lineTo(project(0, columns - 1).dx, size.height - padding * 1.35)
      ..lineTo(project(0, 0).dx, size.height - padding * 1.35)
      ..close();
    canvas.drawPath(shadow, shadowPaint);

    for (var row = rows - 2; row >= 0; row--) {
      for (var column = 0; column < columns - 1; column++) {
        final points = [
          project(row, column),
          project(row, column + 1),
          project(row + 1, column + 1),
          project(row + 1, column),
        ];
        final normalized =
            (normalizedValue(row, column) +
                normalizedValue(row, column + 1) +
                normalizedValue(row + 1, column + 1) +
                normalizedValue(row + 1, column)) /
            4.0;
        fillPaint.color = _surfaceColor(normalized).withValues(alpha: 0.9);

        final path = Path()..addPolygon(points, true);
        canvas.drawPath(path, fillPaint);
        canvas.drawPath(path, gridPaint);

        if (_cellHasDelta(row, column)) {
          canvas.drawPath(path, highlightPaint);
        }
      }
    }
  }

  Color _surfaceColor(double normalized) {
    if (normalized < 0.5) {
      return Color.lerp(
        const Color(0xFF38BDF8),
        const Color(0xFFFACC15),
        normalized / 0.5,
      )!;
    }
    return Color.lerp(
      const Color(0xFFFACC15),
      const Color(0xFFDC2626),
      (normalized - 0.5) / 0.5,
    )!;
  }

  bool _cellHasDelta(int row, int column) {
    if (deltaMatrix.isEmpty) return false;
    for (final r in [row, row + 1]) {
      if (r < 0 || r >= deltaMatrix.length) continue;
      for (final c in [column, column + 1]) {
        if (c < 0 || c >= deltaMatrix[r].length) continue;
        if (deltaMatrix[r][c].abs() > 0.000001) return true;
      }
    }
    return false;
  }

  @override
  bool shouldRepaint(covariant _SurfacePainter oldDelegate) {
    return oldDelegate.matrix != matrix ||
        oldDelegate.deltaMatrix != deltaMatrix;
  }
}

class _EmptyState extends StatelessWidget {
  final IconData icon;
  final String text;

  const _EmptyState({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        children: [
          Icon(icon, color: const Color(0xFF64748B), size: 30),
          const SizedBox(height: 8),
          Text(
            text,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Color(0xFF475569),
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}
