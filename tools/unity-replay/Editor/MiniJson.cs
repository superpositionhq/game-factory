using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace Superposition.LiaoZhaiReplay
{
    /// <summary>
    /// Minimal JSON reader/writer for workflow.jsonl (JsonUtility cannot read free-form objects).
    /// Objects → Dictionary&lt;string, object&gt; (insertion order kept), arrays → List&lt;object&gt;,
    /// integers → long (or double when out of range), other numbers → double.
    /// </summary>
    public static class MiniJson
    {
        public static object Parse(string json)
        {
            int i = 0;
            var v = Value(json, ref i);
            Ws(json, ref i);
            if (i != json.Length)
                throw new FormatException("trailing characters at " + i);
            return v;
        }

        static void Ws(string s, ref int i)
        {
            while (i < s.Length && char.IsWhiteSpace(s[i])) i++;
        }

        static object Value(string s, ref int i)
        {
            Ws(s, ref i);
            if (i >= s.Length) throw new FormatException("unexpected end");
            char c = s[i];
            if (c == '{')
            {
                var d = new OrderedDict();
                i++;
                Ws(s, ref i);
                if (s[i] == '}') { i++; return d; }
                while (true)
                {
                    Ws(s, ref i);
                    var k = Str(s, ref i);
                    Ws(s, ref i);
                    if (s[i++] != ':') throw new FormatException("expected : at " + i);
                    d[k] = Value(s, ref i);
                    Ws(s, ref i);
                    if (s[i] == ',') { i++; continue; }
                    if (s[i] == '}') { i++; return d; }
                    throw new FormatException("expected , or } at " + i);
                }
            }
            if (c == '[')
            {
                var l = new List<object>();
                i++;
                Ws(s, ref i);
                if (s[i] == ']') { i++; return l; }
                while (true)
                {
                    l.Add(Value(s, ref i));
                    Ws(s, ref i);
                    if (s[i] == ',') { i++; continue; }
                    if (s[i] == ']') { i++; return l; }
                    throw new FormatException("expected , or ] at " + i);
                }
            }
            if (c == '"') return Str(s, ref i);
            if (s.Length - i >= 4 && string.CompareOrdinal(s, i, "true", 0, 4) == 0) { i += 4; return true; }
            if (s.Length - i >= 5 && string.CompareOrdinal(s, i, "false", 0, 5) == 0) { i += 5; return false; }
            if (s.Length - i >= 4 && string.CompareOrdinal(s, i, "null", 0, 4) == 0) { i += 4; return null; }
            int st = i;
            bool frac = false;
            while (i < s.Length && "+-0123456789.eE".IndexOf(s[i]) >= 0)
            {
                if (s[i] == '.' || s[i] == 'e' || s[i] == 'E') frac = true;
                i++;
            }
            var num = s.Substring(st, i - st);
            if (num.Length == 0) throw new FormatException("bad value at " + st);
            if (!frac && long.TryParse(num, NumberStyles.Integer, CultureInfo.InvariantCulture, out var lv))
                return lv;
            return double.Parse(num, NumberStyles.Float, CultureInfo.InvariantCulture);
        }

        static string Str(string s, ref int i)
        {
            if (s[i] != '"') throw new FormatException("expected string at " + i);
            i++;
            var sb = new StringBuilder();
            while (true)
            {
                char c = s[i++];
                if (c == '"') return sb.ToString();
                if (c != '\\') { sb.Append(c); continue; }
                char e = s[i++];
                switch (e)
                {
                    case 'n': sb.Append('\n'); break;
                    case 't': sb.Append('\t'); break;
                    case 'r': sb.Append('\r'); break;
                    case 'b': sb.Append('\b'); break;
                    case 'f': sb.Append('\f'); break;
                    case 'u':
                        sb.Append((char)int.Parse(s.Substring(i, 4), NumberStyles.HexNumber));
                        i += 4;
                        break;
                    default: sb.Append(e); break;
                }
            }
        }

        public static string Write(object v)
        {
            var sb = new StringBuilder();
            Write(sb, v);
            return sb.ToString();
        }

        static void Write(StringBuilder sb, object v)
        {
            switch (v)
            {
                case null: sb.Append("null"); break;
                case string s: Quote(sb, s); break;
                case bool b: sb.Append(b ? "true" : "false"); break;
                case double d:
                    sb.Append(double.IsNaN(d) || double.IsInfinity(d) ? "null" : d.ToString("R", CultureInfo.InvariantCulture));
                    break;
                case float f:
                    sb.Append(float.IsNaN(f) || float.IsInfinity(f) ? "null" : f.ToString("R", CultureInfo.InvariantCulture));
                    break;
                case IDictionary d:
                {
                    sb.Append('{');
                    bool first = true;
                    foreach (DictionaryEntry kv in d)
                    {
                        if (!first) sb.Append(',');
                        first = false;
                        Quote(sb, kv.Key.ToString());
                        sb.Append(':');
                        Write(sb, kv.Value);
                    }
                    sb.Append('}');
                    break;
                }
                case IEnumerable e:
                {
                    sb.Append('[');
                    bool first = true;
                    foreach (var x in e)
                    {
                        if (!first) sb.Append(',');
                        first = false;
                        Write(sb, x);
                    }
                    sb.Append(']');
                    break;
                }
                case IFormattable n: sb.Append(n.ToString(null, CultureInfo.InvariantCulture)); break;
                default: Quote(sb, v.ToString()); break;
            }
        }

        static void Quote(StringBuilder sb, string s)
        {
            sb.Append('"');
            foreach (var c in s)
            {
                switch (c)
                {
                    case '"': sb.Append("\\\""); break;
                    case '\\': sb.Append("\\\\"); break;
                    case '\n': sb.Append("\\n"); break;
                    case '\r': sb.Append("\\r"); break;
                    case '\t': sb.Append("\\t"); break;
                    default:
                        if (c < 0x20) sb.Append("\\u").Append(((int)c).ToString("x4"));
                        else sb.Append(c);
                        break;
                }
            }
            sb.Append('"');
        }
    }

    /// <summary>Dictionary that enumerates in insertion order (step values are applied in file order).</summary>
    public sealed class OrderedDict : IDictionary
    {
        readonly Dictionary<string, object> map = new Dictionary<string, object>();
        readonly List<string> keys = new List<string>();

        public object this[object key]
        {
            get => map.TryGetValue((string)key, out var v) ? v : null;
            set
            {
                var k = (string)key;
                if (!map.ContainsKey(k)) keys.Add(k);
                map[k] = value;
            }
        }

        public object Get(string key) => map.TryGetValue(key, out var v) ? v : null;
        public bool Has(string key) => map.ContainsKey(key);
        public IReadOnlyList<string> OrderedKeys => keys;
        public ICollection Keys => keys;
        public ICollection Values => keys.ConvertAll(k => map[k]);
        public bool IsReadOnly => false;
        public bool IsFixedSize => false;
        public int Count => keys.Count;
        public object SyncRoot => this;
        public bool IsSynchronized => false;
        public void Add(object key, object value) => this[key] = value;
        public void Clear() { map.Clear(); keys.Clear(); }
        public bool Contains(object key) => map.ContainsKey((string)key);
        public void Remove(object key) { if (map.Remove((string)key)) keys.Remove((string)key); }
        public void CopyTo(Array array, int index) => throw new NotSupportedException();

        public IDictionaryEnumerator GetEnumerator()
        {
            var list = new List<DictionaryEntry>();
            foreach (var k in keys) list.Add(new DictionaryEntry(k, map[k]));
            return new Enumerator(list);
        }

        IEnumerator IEnumerable.GetEnumerator() => GetEnumerator();

        sealed class Enumerator : IDictionaryEnumerator
        {
            readonly List<DictionaryEntry> list;
            int i = -1;
            public Enumerator(List<DictionaryEntry> l) => list = l;
            public DictionaryEntry Entry => list[i];
            public object Key => list[i].Key;
            public object Value => list[i].Value;
            public object Current => list[i];
            public bool MoveNext() => ++i < list.Count;
            public void Reset() => i = -1;
        }
    }
}
