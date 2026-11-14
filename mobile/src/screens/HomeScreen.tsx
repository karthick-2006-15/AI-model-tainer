import React, { useState, useEffect } from 'react';
import { 
  StyleSheet, 
  Text, 
  View, 
  TextInput, 
  TouchableOpacity, 
  ScrollView, 
  SafeAreaView, 
  StatusBar 
} from 'react-native';
import { JarvisMobileBridge, Telemetry } from '../services/JarvisMobileBridge';

export const HomeScreen: React.FC = () => {
  const [telemetry, setTelemetry] = useState<Telemetry | null>(null);
  const [inputText, setInputText] = useState('');
  const [messages, setMessages] = useState<Array<{ sender: string; text: string }>>([
    { sender: 'jarvis', text: 'JARVIS Mobile Companion linked. Ready for remote commands.' }
  ]);
  const [bridge, setBridge] = useState<JarvisMobileBridge | null>(null);

  useEffect(() => {
    // Connect to host laptop on local network
    const mobileBridge = new JarvisMobileBridge('192.168.1.100', 8000);
    mobileBridge.connect(
      (data) => setTelemetry(data),
      (cmd, resp) => {
        setMessages((prev) => [
          ...prev,
          { sender: 'user', text: cmd },
          { sender: 'jarvis', text: resp }
        ]);
      },
      (challengeId, tool) => {
        console.log(`Level 3 approval needed for: ${tool} (${challengeId})`);
      }
    );
    setBridge(mobileBridge);

    return () => mobileBridge.disconnect();
  }, []);

  const handleSend = () => {
    if (inputText.trim() && bridge) {
      bridge.sendCommand(inputText.trim());
      setInputText('');
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />
      
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>JARVIS COMPANION</Text>
        <Text style={styles.headerStatus}>● LAPTOP LINKED</Text>
      </View>

      {/* Telemetry Panel */}
      <View style={styles.telemetryCard}>
        <Text style={styles.cardTitle}>WINDOWS 11 WORKSTATION</Text>
        <View style={styles.metricsRow}>
          <View style={styles.metricItem}>
            <Text style={styles.metricLabel}>CPU</Text>
            <Text style={styles.metricValue}>{telemetry?.cpu.percent ?? 0}%</Text>
          </View>
          <View style={styles.metricItem}>
            <Text style={styles.metricLabel}>RAM</Text>
            <Text style={styles.metricValue}>{telemetry?.ram.percent ?? 0}%</Text>
          </View>
          <View style={styles.metricItem}>
            <Text style={styles.metricLabel}>STORAGE</Text>
            <Text style={styles.metricValue}>{telemetry?.disk.percent ?? 0}%</Text>
          </View>
        </View>
      </View>

      {/* Conversation Feed */}
      <ScrollView style={styles.feed}>
        {messages.map((m, i) => (
          <View 
            key={i} 
            style={[styles.msgBox, m.sender === 'user' ? styles.userMsg : styles.jarvisMsg]}
          >
            <Text style={styles.msgSender}>{m.sender.toUpperCase()}</Text>
            <Text style={styles.msgText}>{m.text}</Text>
          </View>
        ))}
      </ScrollView>

      {/* Input Bar */}
      <View style={styles.inputContainer}>
        <TextInput
          style={styles.input}
          value={inputText}
          onChangeText={setInputText}
          placeholder="Command laptop (e.g. 'Open VS Code')..."
          placeholderTextColor="#64748b"
        />
        <TouchableOpacity style={styles.sendButton} onPress={handleSend}>
          <Text style={styles.sendText}>SEND</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#030712' },
  header: { padding: 16, borderBottomWidth: 1, borderColor: '#06b6d433', flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  headerTitle: { color: '#06b6d4', fontSize: 16, fontWeight: 'bold', letterSpacing: 1.5 },
  headerStatus: { color: '#34d399', fontSize: 11, fontFamily: 'monospace' },
  telemetryCard: { margin: 16, padding: 14, backgroundColor: '#040e21', borderRadius: 12, borderWidth: 1, borderColor: '#06b6d440' },
  cardTitle: { color: '#94a3b8', fontSize: 10, letterSpacing: 1, marginBottom: 8 },
  metricsRow: { flexDirection: 'row', justifyContent: 'space-between' },
  metricItem: { alignItems: 'center' },
  metricLabel: { color: '#64748b', fontSize: 10 },
  metricValue: { color: '#06b6d4', fontSize: 16, fontWeight: 'bold' },
  feed: { flex: 1, paddingHorizontal: 16 },
  msgBox: { padding: 12, borderRadius: 10, marginBottom: 10 },
  userMsg: { backgroundColor: '#083344', alignSelf: 'flex-end', maxWidth: '85%' },
  jarvisMsg: { backgroundColor: '#040e21', alignSelf: 'flex-start', maxWidth: '85%', borderWidth: 1, borderColor: '#06b6d420' },
  msgSender: { color: '#06b6d4', fontSize: 9, marginBottom: 4, fontWeight: 'bold' },
  msgText: { color: '#f1f5f9', fontSize: 13, lineHeight: 18 },
  inputContainer: { padding: 12, borderTopWidth: 1, borderColor: '#06b6d420', flexDirection: 'row' },
  input: { flex: 1, backgroundColor: '#020617', color: '#f8fafc', paddingHorizontal: 14, paddingVertical: 10, borderRadius: 8, borderWidth: 1, borderColor: '#0e7490', fontSize: 13 },
  sendButton: { marginLeft: 8, backgroundColor: '#0891b2', paddingHorizontal: 16, justifyContent: 'center', borderRadius: 8 },
  sendText: { color: '#ffffff', fontWeight: 'bold', fontSize: 12 }
});
